"""ReportFactsCollector — LLM 호출 전 사실 선수집의 키 완전성·실패 격리 (Fake 포트, DB 없음)."""

import json
from datetime import date
import time

import pytest

from apps.agent.app.ports.output.agent_port import (
    EventAnalogFactsPort,
    FinanceFactsPort,
    FundingFactsPort,
    NewsLinksPort,
    RegionalEventsPort,
    QuestionBudgetPort,
    RegionFactsPort,
    VerdictFactsPort,
)
from apps.agent.app.use_cases.report_facts import FACTS_KEYS, ReportFactsCollector


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
        self,
        industry_id: str | None,
        external_funding_need: int | None,
        stage: str | None,
        region_code: str | None = None,
    ) -> dict:
        self.calls.append((industry_id, external_funding_need, stage, region_code))
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


class FakeNewsLinks(NewsLinksPort):
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def mentioning(self, name: str, limit: int) -> list[dict]:
        self.calls.append((name, limit))
        return [{"title": "역삼동 한식 상권 기사", "url": "https://news.example/1", "published_at": "2026-09-01", "press": None}]


class FakeRegionalEvents(RegionalEventsPort):
    """최근 것 먼저 — 2026년 6건과 3년 넘은 2023년 1건."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def for_region(self, region_code: str) -> list[dict]:
        self.calls.append(region_code)
        recent = [{"start_date": f"2026-0{m}-01", "name": f"사건 {m}", "source": "서울 열린데이터광장 OA-16096 서울시 대규모점포 인허가 정보"} for m in range(6, 0, -1)]
        return [*recent, {"start_date": "2023-10-05", "name": "오래된 사건", "source": "서울 열린데이터광장 OA-15818 서울시 공동주택 아파트 정보"}]


def _collector(region=None, verdict=None, funding=None, news=None, regional=None) -> ReportFactsCollector:
    return ReportFactsCollector(
        region_facts=region or FakeRegionFacts(),
        verdict_facts=verdict or FakeVerdictFacts(),
        funding_facts=funding or FakeFundingFacts(),
        news_links=news or FakeNewsLinks(),
        regional_events=regional,
        today=lambda: date(2026, 10, 6),
    )


def test_열다섯_키를_빠짐없이_모은다():
    """프론트 시각 자료가 키 하나에 하나씩 달린다 — 키가 빠지면 그림이 사라진다 (설계서 §5)."""
    facts = _collector().collect("1168064000", "korean_food", 50_000_000)

    assert list(facts) == list(FACTS_KEYS)
    assert len(FACTS_KEYS) == 15 and FACTS_KEYS[-1] == "finance"


class FakeFinanceFacts(FinanceFactsPort):
    def __init__(self, failing: bool = False) -> None:
        self._failing = failing

    def prefill(self, region_code: str, industry_id: str) -> dict:
        if self._failing:
            raise RuntimeError("프리필 조회 실패")
        return {"available": True, "loan_rate": {"value": 0.0405, "unit": "비율", "basis": {"period": "202608"}, "caveat": "공시"}}


class FakeQuestionBudget(QuestionBudgetPort):
    def parse(self, question: str) -> int | None:
        return 50_000_000 if "5천만" in question else None


def _with_new_ports(finance=None) -> ReportFactsCollector:
    return ReportFactsCollector(
        region_facts=FakeRegionFacts(),
        verdict_facts=FakeVerdictFacts(),
        funding_facts=FakeFundingFacts(),
        news_links=FakeNewsLinks(),
        finance_facts=finance or FakeFinanceFacts(),
        question_budget=FakeQuestionBudget(),
    )


def test_자금_계획_프리필을_싣고_실패하면_그_자리만_비운다():
    assert _with_new_ports().collect("1168064000", "korean_food")["finance"]["loan_rate"]["value"] == 0.0405
    failed = _with_new_ports(FakeFinanceFacts(failing=True)).collect("1168064000", "korean_food")["finance"]
    assert failed["available"] is False and "프리필 조회 실패" in failed["reason"]


def test_폼_예산이_없으면_질문_속_금액을_예산으로_싣는다():
    collector = _with_new_ports()
    assert collector.collect("1168064000", "hair_salon", None, "모아 둔 돈이 5천만 원")["budget"] == 50_000_000
    assert collector.collect("1168064000", "hair_salon", 70_000_000, "모아 둔 돈이 5천만 원")["budget"] == 70_000_000
    assert collector.collect("1168064000", "hair_salon", None, None)["budget"] is None


class FakeAnalogFacts(EventAnalogFactsPort):
    def __init__(self, failing: bool = False) -> None:
        self._failing = failing
        self.calls: list[tuple[str, str | None, str | None]] = []

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
        news_links=FakeNewsLinks(),
        analog_facts=analog,
    )
    facts = collector.collect("1168064000", "cafe", None, "바이러스가 돌면?")

    assert analog.calls == [("cafe", "바이러스가 돌면?")]
    assert facts["analogs"]["analogs"][0]["event_id"] == "outbreak-covid19-20200120"
    # LLM이 옮길 고정 문장을 코드가 붙인다
    assert facts["analogs"]["outlooks"][0]["recommended_sentence"] == (
        "근로시간이 줄었던 시기에 서울 전체에서 다른 업종보다 상대적으로 잘 버틴 업종은 헬스장이었습니다."
    )


def test_유사_사례_조회가_실패해도_나머지는_뜬다():
    collector = ReportFactsCollector(
        region_facts=FakeRegionFacts(),
        verdict_facts=FakeVerdictFacts(),
        funding_facts=FakeFundingFacts(),
        news_links=FakeNewsLinks(),
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


def test_뉴스는_동_이름이_나온_기사의_원문_링크만_싣는다():
    """네이버 검색 결과는 링크로만 보여 준다 — 발췌는 싣지 않는다(검색 API 특약 2.2·2.3). 동 번호는 떼고 찾는다."""
    news = FakeNewsLinks()

    facts = _collector(news=news).collect("1168064000", "korean_food", None)

    assert news.calls == [("역삼", 3)]
    assert facts["news"] == [
        {"title": "역삼동 한식 상권 기사", "url": "https://news.example/1", "published_at": "2026-09-01", "press": None}
    ]


def test_지원사업_후보는_업종과_동으로_받는다():
    """조달 필요액·단계는 아직 모른다. 동은 다른 구 전용 공고를 빼는 데 쓴다."""
    funding = FakeFundingFacts()

    facts = _collector(funding=funding).collect("1168064000", "korean_food", None)

    assert funding.calls == [("korean_food", None, None, "1168064000")]
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


def test_요약이_실패하면_지역_키는_코드로_메우고_뉴스는_찾지_않는다():
    """이름을 못 얻어도 나머지 수집을 멈추지 않는다. 동 이름 없이 찾을 뉴스는 없다."""
    news = FakeNewsLinks()
    collector = _collector(region=FakeRegionFacts(failing={"summary"}), news=news)

    facts = collector.collect("1168064000", "korean_food", None)

    assert facts["region"]["name"] == "1168064000"  # FE는 string으로 읽는다 — null을 주지 않는다
    assert facts["region"]["industry_name"] == "korean_food"
    assert facts["region"]["code"] == "1168064000"
    assert news.calls == [] and facts["news"] == []


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


def test_지역_사건은_동_코드로_찾아_최근_3년_것을_최대_5건_싣는다():
    regional = FakeRegionalEvents()

    facts = _collector(regional=regional).collect("1168064000", "korean_food", None)

    assert regional.calls == ["1168064000"]
    assert [e["name"] for e in facts["regional_events"]] == ["사건 6", "사건 5", "사건 4", "사건 3", "사건 2"]


def test_지역_사건_원천이_없으면_그_자리만_자료_없음이다():
    facts = _collector().collect("1168064000", "korean_food", None)

    assert facts["regional_events"]["available"] is False
