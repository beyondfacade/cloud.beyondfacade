"""지원사업 하이브리드 검색 — 규칙으로 거른 뒤 질문 유사도로 정렬 (설계서 2026-10-07 §2·§3, DB 없음)."""

import logging
from datetime import date

import pytest
from fastapi.testclient import TestClient

from apps.funding.adapter.outbound.gateways import rag_question_ranker_gateway
from apps.funding.adapter.outbound.gateways.rag_question_ranker_gateway import (
    RagQuestionRankerGateway,
)
from apps.funding.app.ports.output.funding_program_port import (
    DistrictNameLookupPort,
    FundingProgramRepositoryPort,
    FundingSearchGatewayPort,
    QuestionRankerPort,
    SeoulDistrictNamesPort,
)
from apps.funding.app.use_cases import funding_program_interactor as interactor_module
from apps.funding.app.use_cases.funding_program_interactor import FundingProgramInteractor
from apps.funding.dependencies.funding_program_dependencies import (
    get_funding_program_use_case,
)
from apps.funding.domain.entities.funding_program_entity import FundingProgram
from apps.funding.domain.services.candidates import select_candidates
from apps.funding.domain.services.relevance import order_by_relevance, relevant_ids
from main import app

_SEOUL_GU = frozenset({"강남구", "관악구"})
_TODAY = date(2026, 10, 7)


def _program(n: int, *, title: str | None = None, field_category: str = "경영") -> FundingProgram:
    return FundingProgram(
        program_id=f"p{n:02d}",
        source="bizinfo",
        title=title or f"공고 {n}",
        org="서울특별시",
        url=f"https://example.com/{n}",
        apply_period="",
        target_text="소상공인",
        hashtags="경영,서울",
        field_category=field_category,
        deadline=date(2026, 11, n),
    )


def _ids(items) -> list[str]:
    return [item.program.program_id for item in items]


# --- 도메인: 정렬 정책 ---


def test_질문과_가까운_것을_앞에_두고_색인_없는_공고는_규칙_순서대로_뒤에_붙인다():
    candidates = select_candidates(
        [_program(n) for n in range(1, 6)], seoul_district_names=_SEOUL_GU, today=_TODAY
    )  # 규칙 순서 p01..p05

    ordered = order_by_relevance(candidates, ["p04", "p02", "p99"])  # p99는 후보 밖

    assert _ids(ordered) == ["p04", "p02", "p01", "p03", "p05"]


def test_기준선은_절대_상한_안이면서_1등과_차이가_작은_것만_가까운_순으로_남긴다():
    # 1등 0.30 → 0.38까지(1등 차이) / 1등 0.50 → 0.54까지(절대 상한)
    assert relevant_ids([("a", 0.30), ("b", 0.38), ("c", 0.39)]) == ["a", "b"]
    assert relevant_ids([("a", 0.50), ("b", 0.54), ("c", 0.55)]) == ["a", "b"]
    assert relevant_ids([("a", 0.60)]) == []
    assert relevant_ids([]) == []


# --- 인터랙터: 질문 없음 / 있음 / 랭커 실패 ---


class _Repository(FundingProgramRepositoryPort):
    def __init__(self, programs):
        self._programs = programs

    def upsert(self, programs):
        raise NotImplementedError

    def refresh_expirations(self, today):
        raise NotImplementedError

    def list_open(self, limit):
        raise NotImplementedError

    def list_open_all(self):
        return self._programs


class _Gateway(FundingSearchGatewayPort):
    def fetch_all(self):
        return []


class _Districts(SeoulDistrictNamesPort, DistrictNameLookupPort):
    def names(self):
        return _SEOUL_GU

    def name_of(self, district_code):
        return {"11680": "강남구"}.get(district_code)


class _Ranker(QuestionRankerPort):
    """id 내림차순을 "질문과 가까운 순"으로 본다 — 규칙 순서(오름차순)와 반대라 정렬 여부가 드러난다.

    기본 거리 0.30(기준선 안). `far`는 0.90(기준선 밖), `unindexed`는 결과에서 빠진다(색인 없음).
    """

    def __init__(self, far=(), unindexed=()):
        self.calls: list[tuple[str, list[str]]] = []
        self._far = set(far)
        self._unindexed = set(unindexed)

    def rank(self, question, program_ids):
        self.calls.append((question, program_ids))
        scored = [
            (program_id, 0.90 if program_id in self._far else 0.30)
            for program_id in sorted(program_ids, reverse=True)
            if program_id not in self._unindexed
        ]
        return sorted(scored, key=lambda pair: pair[1])


class _DownRanker(QuestionRankerPort):
    def rank(self, question, program_ids):
        raise ConnectionError("Ollama 연결 거부")


def _interactor(programs, ranker=None):
    districts = _Districts()
    return FundingProgramInteractor(
        repository=_Repository(programs),
        gateway=_Gateway(),
        seoul_districts=districts,
        district_lookup=districts,
        ranker=ranker,
    )


_TWELVE = [_program(n) for n in range(1, 13)]


@pytest.mark.parametrize("question", [None, "   "])
def test_질문이_없거나_비면_랭커를_부르지_않고_마감_임박_순이다(question):
    ranker = _Ranker()

    result = _interactor(_TWELVE, ranker).list_candidates(None, None, None, question=question)

    assert ranker.calls == []
    assert result.order == "deadline"
    assert _ids(result.candidates) == [f"p{n:02d}" for n in range(1, 9)]


def test_질문이_있으면_규칙_통과_전체를_정렬해_상위_8건을_고른다():
    ranker = _Ranker()

    result = _interactor(_TWELVE, ranker).list_candidates(None, None, None, question="청년 대출")

    assert ranker.calls == [("청년 대출", [f"p{n:02d}" for n in range(1, 13)])]  # 8건이 아니라 전체
    assert result.order == "relevance"
    assert _ids(result.candidates) == [f"p{n:02d}" for n in range(12, 4, -1)]


def test_랭커가_실패하면_규칙_순서로_돌려주고_경고를_한_줄_남긴다(caplog, monkeypatch):
    # 세션 픽스처의 alembic fileConfig가 이미 만들어진 로거를 꺼 둔다 — 이 로거만 다시 켠다
    monkeypatch.setattr(interactor_module.LOGGER, "disabled", False)
    with caplog.at_level(logging.WARNING):
        result = _interactor(_TWELVE, _DownRanker()).list_candidates(None, None, None, question="청년 대출")

    assert result.order == "deadline"
    assert _ids(result.candidates) == [f"p{n:02d}" for n in range(1, 9)]
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


def test_기준선을_통과한_공고가_없으면_재정렬하지_않고_deadline이다():
    ranker = _Ranker(far=[program.program_id for program in _TWELVE])

    result = _interactor(_TWELVE, ranker).list_candidates(None, None, None, question="인테리어 비용")

    assert result.order == "deadline"
    assert _ids(result.candidates) == [f"p{n:02d}" for n in range(1, 9)]


def test_지원_정보는_질문이_없으면_검색_결과가_없다():
    ranker = _Ranker()

    guide = _interactor(_TWELVE, ranker).support_guide(None, None)

    assert guide.search is None
    assert ranker.calls == []


def test_지원_정보_검색은_묶음_구분_없이_기준선을_통과한_공고_전부를_가까운_순으로_내고_다른_구_전용은_뺀다():
    programs = [*_TWELVE, _program(13, title="관악구 소상공인 지원"), _program(14, field_category="금융")]
    ranker = _Ranker(far=["p12"], unindexed=["p11"])

    guide = _interactor(programs, ranker).support_guide("1168064000", None, question="인테리어 비용")

    assert "p13" not in ranker.calls[0][1]
    assert guide.search.query == "인테리어 비용"
    assert guide.search.available is True
    # 8건 상한 없음 · 기준선 밖(p12)과 색인 없는 공고(p11)는 넣지 않는다
    assert _ids(guide.search.items) == ["p14", *[f"p{n:02d}" for n in range(10, 0, -1)]]


def test_지원_정보_검색은_기준선을_통과한_공고가_없으면_빈_결과다():
    ranker = _Ranker(far=[program.program_id for program in _TWELVE])

    guide = _interactor(_TWELVE, ranker).support_guide(None, None, question="인테리어 비용")

    assert guide.search.available is True
    assert guide.search.items == []


def test_지원_정보_검색은_랭커가_실패하면_쓸_수_없다고_하고_규칙_순서로_채우지_않는다():
    guide = _interactor(_TWELVE, _DownRanker()).support_guide(None, None, question="인테리어 비용")

    assert guide.search.available is False
    assert guide.search.items == []
    assert _ids(guide.others)  # 세 묶음은 그대로


def test_질문은_앞뒤_공백을_자르고_200자에서_자른다():
    ranker = _Ranker()

    guide = _interactor(_TWELVE, ranker).support_guide(None, None, question=f"  {'가' * 250}  ")

    assert guide.search.query == "가" * 200
    assert ranker.calls[0][0] == "가" * 200


# --- 라우터 계약 (설계서 §3) ---


def _get(path: str, ranker=None):
    app.dependency_overrides[get_funding_program_use_case] = lambda: _interactor(_TWELVE, ranker or _Ranker())
    try:
        return TestClient(app).get(path)
    finally:
        app.dependency_overrides.clear()


def test_공고_후보_API는_q가_있으면_order가_relevance이고_없으면_deadline이다():
    with_q = _get("/funding/candidates?q=청년 대출").json()
    without_q = _get("/funding/candidates").json()

    assert with_q["order"] == "relevance"
    assert with_q["candidates"][0]["program_id"] == "p12"
    assert without_q["order"] == "deadline"


def test_지원_정보_API는_q가_없으면_search가_null이다():
    assert _get("/funding/support").json()["search"] is None


def test_지원_정보_API는_q로_찾은_공고를_search에_싣는다():
    search = _get("/funding/support?q=인테리어 비용").json()["search"]

    assert search["query"] == "인테리어 비용"
    assert search["available"] is True
    assert len(search["items"]) == 12
    assert {"program_id", "title", "why", "district_match", "industry_match"} <= set(search["items"][0])


def test_지원_정보_API는_검색을_못_쓰면_available이_false다():
    search = _get("/funding/support?q=인테리어 비용", _DownRanker()).json()["search"]

    assert search == {"query": "인테리어 비용", "available": False, "items": []}


# --- rag BC 게이트웨이 (ACL) ---


def test_랭커_게이트웨이는_funding_접두로_rag를_부르고_program_id로_되돌린다(monkeypatch):
    calls = []

    class _RagSearch:
        def rank_within(self, query, chunk_ids):
            calls.append((query, chunk_ids))
            return [("funding:p02", 0.31)]  # 색인 없는 p01은 빠져 온다

    timeouts = []

    def _use_case(provider, timeout):
        timeouts.append(timeout)
        return _RagSearch()

    monkeypatch.setattr(rag_question_ranker_gateway, "get_rag_search_use_case", _use_case)

    ranked = RagQuestionRankerGateway().rank("청년 대출", ["p01", "p02"])

    assert calls == [("청년 대출", ["funding:p01", "funding:p02"])]
    assert ranked == [("p02", 0.31)]
    # 화면·리포트가 기다리는 경로 — 색인용 120초가 아니라 짧게 끊고 규칙 순서로 돌아간다(설계서 §2-4)
    assert timeouts == [5.0]
