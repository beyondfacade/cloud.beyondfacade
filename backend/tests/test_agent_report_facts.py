"""ReportFactsCollector — LLM 호출 전 사실 선수집의 키 완전성·실패 격리 (Fake 포트, DB 없음)."""

import json
import time
from datetime import datetime

import pytest

from apps.agent.app.ports.output.agent_port import (
    EventAnalogFactsPort,
    FundingFactsPort,
    RegionFactsPort,
    VerdictFactsPort,
)
from apps.agent.app.use_cases.report_facts import FACTS_KEYS, ReportFactsCollector
from apps.rag.app.ports.input.rag_use_case import RagSearchUseCase
from apps.rag.domain.entities.rag_chunk_entity import RagHit


class FakeRegionFacts(RegionFactsPort):
    def __init__(
        self,
        failing: set[str] = frozenset(),
        slow: dict[str, float] | None = None,
        industry_shocks: bool = True,
    ) -> None:
        self._failing = failing
        self._slow = slow or {}
        self._industry_shocks = industry_shocks
        self.shock_calls: list[str | None] = []

    def _guard(self, name: str) -> None:
        if name in self._failing:
            raise RuntimeError(f"{name} 조회 실패")
        if name in self._slow:
            time.sleep(self._slow[name])

    def metrics_history(self, region_code: str, industry_id: str) -> list[dict]:
        self._guard("metrics_history")
        return [{"year": 2024, "store_count": 120, "closure_rate": 0.12, "growth_rate": -0.01}]

    def summary(self, region_code: str, industry_id: str) -> dict:
        self._guard("summary")
        return {
            "region_code": region_code,
            "name": "역삼1동",
            "industry_id": industry_id,
            "industry_name": "한식",
            "cards": [],
        }

    def population(self, region_code: str) -> dict:
        self._guard("population")
        return {"region_code": region_code, "period": "202608", "school_age_population": 3}

    def shocks(self, industry_id: str | None, limit: int) -> list[dict]:
        self._guard("shocks")
        self.shock_calls.append(industry_id)
        if industry_id is not None and not self._industry_shocks:
            return []  # 한식처럼 원천에 업종 영향 행이 없는 업종
        return [{"event_id": "E1", "name": "재난지원금", "limit_seen": limit}]

    def latest_rates(self) -> dict:
        return {"loan_facility": 4.05}

    def neighborhood_profile(self, region_code: str) -> dict:
        self._guard("neighborhood_profile")
        return {
            "region_code": region_code,
            "neighborhood_type": "office",
            "block_intensities": {"morning": 0.8, "day": 1.4, "evening": 1.1, "night": 0.4},
        }

    def hour_gap(self, region_code: str, industry_id: str) -> dict:
        self._guard("hour_gap")
        return {"available": True, "year_quarter": "20252", "bands": []}

    def commerce_change_detail(self, region_code: str) -> dict:
        self._guard("commerce_change_detail")
        return {"available": True, "change_name": "다이나믹"}


class FakeVerdictFacts(VerdictFactsPort):
    def __init__(self, failing: set[str] = frozenset()) -> None:
        self._failing = failing

    def verdict(self, region_code: str, industry_id: str) -> dict:
        if "verdict" in self._failing:
            raise ValueError("판정 조회 실패")
        return {"available": True, "verdict_code": "red"}

    def alternatives(self, region_code: str, industry_id: str) -> dict:
        return {"available": True, "industries": [], "regions": []}


class FakeFundingFacts(FundingFactsPort):
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def candidates(
        self, industry_id: str | None, external_funding_need: int | None, stage: str | None
    ) -> dict:
        self.calls.append((industry_id, external_funding_need, stage))
        return {
            "candidates": [
                {"program_id": "P1", "title": "청년창업자금", "field_category": "금융"},
                {"program_id": "P2", "title": "대상 없는 공고"},
            ],
            "industry_id": industry_id,
            "external_funding_need": external_funding_need,
            "stage": stage,
            "disclaimer": "자격 확정이 아니다",
        }


class FakeNewsSearch(RagSearchUseCase):
    def __init__(self) -> None:
        self.queries: list[tuple[str, str | None]] = []

    def search(self, query: str, top_k: int = 5, source_type: str | None = None) -> list[RagHit]:
        self.queries.append((query, source_type))
        return [
            RagHit(
                chunk_id="news:1",
                source_type="news",
                source_id="1",
                content="역삼동 한식 상권 기사",
                score=0.8,
                url="https://news.example/1",
                org="한국일보",
                published_at=datetime(2026, 9, 1, 12, 0),
            )
        ]


def _collector(region=None, verdict=None, funding=None, news=None) -> ReportFactsCollector:
    return ReportFactsCollector(
        region_facts=region or FakeRegionFacts(),
        verdict_facts=verdict or FakeVerdictFacts(),
        funding_facts=funding or FakeFundingFacts(),
        news_search=news or FakeNewsSearch(),
    )


def test_열세_키를_빠짐없이_모은다():
    """프론트 시각 자료가 키 하나에 하나씩 달린다 — 키가 빠지면 그림이 사라진다 (설계서 §5)."""
    facts = _collector().collect("1168064000", "korean_food", 50_000_000)

    assert list(facts) == list(FACTS_KEYS)
    assert len(FACTS_KEYS) == 13


class FakeAnalogFacts(EventAnalogFactsPort):
    def __init__(self, failing: bool = False) -> None:
        self._failing = failing
        self.calls: list[tuple[str, str | None]] = []

    def analogs(self, industry_id: str, question: str | None) -> dict:
        self.calls.append((industry_id, question))
        if self._failing:
            raise RuntimeError("흐름 조회 실패")
        return {
            "available": True,
            "analogs": [{"event_id": "outbreak-covid19-20200120", "series": [{"role": "target", "industry_name": "카페"}]}],
            "outlooks": [{"category": "work_hours", "recommended": [{"industry_id": "gym", "industry_name": "헬스장"}]}],
        }


def test_유사_사례는_업종과_질문으로_조회한다():
    analog = FakeAnalogFacts()
    collector = ReportFactsCollector(
        region_facts=FakeRegionFacts(),
        verdict_facts=FakeVerdictFacts(),
        funding_facts=FakeFundingFacts(),
        news_search=FakeNewsSearch(),
        analog_facts=analog,
    )
    facts = collector.collect("1168064000", "cafe", None, "바이러스가 돌면?")

    assert analog.calls == [("cafe", "바이러스가 돌면?")]
    assert facts["analogs"]["analogs"][0]["event_id"] == "outbreak-covid19-20200120"
    # LLM이 옮길 고정 문장을 코드가 붙인다
    assert facts["analogs"]["outlooks"][0]["recommended_sentence"] == (
        "근로시간이 줄었던 시기에 다른 업종보다 상대적으로 잘 버틴 업종은 헬스장이었습니다."
    )


def test_유사_사례_조회가_실패해도_나머지는_뜬다():
    collector = ReportFactsCollector(
        region_facts=FakeRegionFacts(),
        verdict_facts=FakeVerdictFacts(),
        funding_facts=FakeFundingFacts(),
        news_search=FakeNewsSearch(),
        analog_facts=FakeAnalogFacts(failing=True),
    )
    facts = collector.collect("1168064000", "cafe", None)

    assert facts["analogs"]["available"] is False
    assert facts["verdict"]["available"] is True


def test_유사_사례_포트가_없으면_자료_없음이다():
    assert _collector().collect("1168064000", "cafe", None)["analogs"]["available"] is False


def test_지역_키는_코드와_이름_업종명을_함께_싣는다():
    facts = _collector().collect("1168064000", "korean_food", None)

    assert facts["region"] == {
        "code": "1168064000",
        "name": "역삼1동",
        "industry_id": "korean_food",
        "industry_name": "한식",
    }


def test_예산은_받은_값을_그대로_싣는다():
    assert _collector().collect("1168064000", "korean_food", 50_000_000)["budget"] == 50_000_000
    assert _collector().collect("1168064000", "korean_food", None)["budget"] is None


def test_뉴스는_동_이름과_업종명으로_검색한다():
    news = FakeNewsSearch()

    facts = _collector(news=news).collect("1168064000", "korean_food", None)

    assert news.queries == [("역삼1동 한식", "news")]
    assert facts["news"][0]["org"] == "한국일보"
    assert facts["news"][0]["published_at"] == "2026-09-01T12:00:00"


def test_지원사업_후보는_업종만_걸러_받는다():
    """get_funding_candidates의 기본값과 같다 — 조달 필요액·단계는 아직 모른다."""
    funding = FakeFundingFacts()

    facts = _collector(funding=funding).collect("1168064000", "korean_food", None)

    assert funding.calls == [("korean_food", None, None)]
    assert facts["funding_candidates"][0]["title"] == "청년창업자금"


def test_지원사업_후보는_공고_배열_그대로_싣는다():
    """프론트 계약은 배열이다 (설계서 §3-1) — dict로 싸면 카드가 한 장도 안 뜬다."""
    facts = _collector().collect("1168064000", "korean_food", None)

    assert isinstance(facts["funding_candidates"], list)
    assert [c["program_id"] for c in facts["funding_candidates"]] == ["P1", "P2"]


def test_지원사업_후보에_대상을_지어_넣지_않는다():
    """공고의 분야(`field_category`)는 대상이 아니다 — "대상: 금융"은 거짓말이다.

    `target`이 없으면 프론트가 '대상' 줄을 지운다. 분야 자체는 그대로 남긴다.
    """
    candidates = _collector().collect("1168064000", "korean_food", None)["funding_candidates"]

    assert all("target" not in candidate for candidate in candidates)
    assert candidates[0]["field_category"] == "금융"


def test_프로필은_시간대_블록_강도를_함께_싣는다():
    """복원한 하루 흐름 막대가 이 키만 읽는다 — 빠지면 그림이 사라진다 (설계서 §4-2)."""
    profile = _collector().collect("1168064000", "korean_food", None)["profile"]

    assert profile["block_intensities"] == {
        "morning": 0.8,
        "day": 1.4,
        "evening": 1.1,
        "night": 0.4,
    }


def test_한_항목이_실패해도_나머지_사실은_나간다():
    """수집은 전부 아니면 무가 아니다 — 실패한 그림 자리만 '자료 없음'이 된다 (설계서 §3-1)."""
    collector = _collector(region=FakeRegionFacts(failing={"hour_gap"}))

    facts = collector.collect("1168064000", "korean_food", None)

    assert facts["hour_gap"] == {
        "available": False,
        "reason": "RuntimeError: hour_gap 조회 실패",
    }
    assert facts["metrics_history"][0]["year"] == 2024
    assert facts["verdict"]["verdict_code"] == "red"


def test_요약이_실패해도_지역_키와_뉴스_검색은_코드로_돈다():
    """이름을 못 얻어도 나머지 수집을 멈추지 않는다."""
    news = FakeNewsSearch()
    collector = _collector(region=FakeRegionFacts(failing={"summary"}), news=news)

    facts = collector.collect("1168064000", "korean_food", None)

    assert facts["region"]["name"] == "1168064000"  # FE는 string으로 읽는다 — null을 주지 않는다
    assert facts["region"]["industry_name"] == "korean_food"
    assert facts["region"]["code"] == "1168064000"
    assert news.queries == [("1168064000 korean_food", "news")]


def test_판정이_실패하면_그_자리만_이유와_함께_비운다():
    collector = _collector(verdict=FakeVerdictFacts(failing={"verdict"}))

    facts = collector.collect("1168064000", "korean_food", None)

    assert facts["verdict"] == {"available": False, "reason": "ValueError: 판정 조회 실패"}
    assert facts["alternatives"]["available"] is True


def test_수집_결과는_그대로_JSON으로_실린다():
    """facts는 SSE 프레임과 LLM 첫 메시지에 JSON으로 들어간다 — 직렬화 불가 값이 섞이면 안 된다."""
    facts = _collector().collect("1168064000", "korean_food", 50_000_000)

    assert json.loads(json.dumps(facts, ensure_ascii=False))["region"]["name"] == "역삼1동"


@pytest.mark.parametrize("key", ["profile", "commerce_change", "population", "shocks"])
def test_타_BC_사실도_각자_격리된다(key: str):
    failing = {
        "profile": "neighborhood_profile",
        "commerce_change": "commerce_change_detail",
        "population": "population",
        "shocks": "shocks",
    }[key]
    collector = _collector(region=FakeRegionFacts(failing={failing}))

    facts = collector.collect("1168064000", "korean_food", None)

    assert facts[key]["available"] is False
    assert facts["metrics_history"]  # 나머지는 그대로


# --- 충격은 업종이 비면 전 업종 공통으로 되돌린다 (리뷰 라운드 1) ---


def test_업종_충격이_있으면_업종별로_표시한다():
    region = FakeRegionFacts(industry_shocks=True)

    facts = _collector(region=region).collect("1168064000", "korean_food", None)

    assert region.shock_calls == ["korean_food"]
    assert facts["shocks"][0]["industry_specific"] is True


def test_업종_충격이_없으면_전_업종_공통_충격으로_되돌린다():
    """한식처럼 원천에 업종 영향 행이 없는 업종에서 reasons 절의 충격 재료가 통째로 비지 않게."""
    region = FakeRegionFacts(industry_shocks=False)

    facts = _collector(region=region).collect("1168064000", "korean_food", None)

    assert region.shock_calls == ["korean_food", None]
    assert facts["shocks"][0]["industry_specific"] is False


# --- 수집은 항목을 동시에 돈다 (리뷰 라운드 1) ---


def test_느린_항목이_나머지를_기다리게_하지_않는다():
    """항목마다 제 세션을 여는 독립 조회다 — 직렬이면 0.6초, 동시면 0.2초대."""
    region = FakeRegionFacts(
        slow={"metrics_history": 0.2, "population": 0.2, "neighborhood_profile": 0.2}
    )

    started = time.monotonic()
    facts = _collector(region=region).collect("1168064000", "korean_food", None)
    elapsed = time.monotonic() - started

    assert elapsed < 0.45, f"동시 수집이 아니다 ({elapsed:.2f}초)"
    assert list(facts) == list(FACTS_KEYS)  # 순서는 계약이다
    assert facts["metrics_history"][0]["year"] == 2024
