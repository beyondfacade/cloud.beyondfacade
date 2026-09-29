"""백테스트 — 직전 분기 라벨·집계(도메인)·인터랙터가 상한을 넘기고 결과와 조인하는지 (Fake 포트) (설계서 §13)."""

from datetime import date, datetime, timezone

import pytest

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    EntrantOutcome,
    JudgedIndustry,
    LatestStoreCount,
    RegionContext,
    StoreSignalStat,
)
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    EntrantOutcomePort,
    IndustryCatalogPort,
    RegionCatalogPort,
    RegionContextPort,
    RegionIndustryVerdictRepositoryPort,
    StoreSignalStatsPort,
)
from apps.verdict.app.use_cases.region_industry_verdict_interactor import RegionIndustryVerdictInteractor
from apps.verdict.domain.entities.region_industry_verdict_entity import RegionIndustryVerdict, SignalResult
from apps.verdict.domain.services.backtest import (
    GATE_POLICIES,
    OutcomeBucket,
    quarter_before,
    quarter_of,
    reinclusion_gate,
    shift_quarter,
    summarize,
    summarize_signals,
)

_AT = datetime(2026, 9, 29, tzinfo=timezone.utc)


def _v(region: str, industry: str, code: str) -> RegionIndustryVerdict:
    return RegionIndustryVerdict(region, industry, code, 0, 0, (), _AT)


def test_직전_분기_라벨():
    assert quarter_before(date(2022, 6, 30)) == "20221"
    assert quarter_before(date(2026, 1, 15)) == "20254"
    assert quarter_before(date(2024, 12, 31)) == "20243"


def test_분기_보조_함수():
    assert quarter_of(date(2022, 6, 30)) == "20222"
    assert quarter_of(date(2022, 7, 1)) == "20223"
    assert shift_quarter("20254", -4) == "20244"
    assert shift_quarter("20221", -1) == "20214"
    assert shift_quarter("20214", 1) == "20221"


def test_집계는_판정_코드별_조합_개업_폐업을_전체와_업종별로_센다():
    verdicts = [_v("r1", "cafe", "red"), _v("r2", "cafe", "clear"), _v("r3", "cafe", "red"), _v("r1", "pub", "clear")]
    outcomes = [
        EntrantOutcome("r1", "cafe", opened=10, closed_within=6),
        EntrantOutcome("r2", "cafe", opened=20, closed_within=4),
        EntrantOutcome("r1", "pub", opened=5, closed_within=1),
        EntrantOutcome("r9", "cafe", opened=7, closed_within=7),  # 판정 없는 동 → 무시
    ]
    buckets = summarize(verdicts, outcomes)
    overall = {b.verdict_code: b for b in buckets if b.industry_id is None}
    assert (overall["red"].pairs, overall["red"].opened, overall["red"].closed) == (2, 10, 6)  # r3는 개업 0
    assert (overall["clear"].pairs, overall["clear"].opened, overall["clear"].closed) == (2, 25, 5)
    assert overall["red"].rate == 0.6 and overall["clear"].rate == 0.2
    cafe = {b.verdict_code: b for b in buckets if b.industry_id == "cafe"}
    assert (cafe["clear"].opened, cafe["clear"].closed) == (20, 4)
    assert {b.verdict_code for b in buckets if b.industry_id == "pub"} == {"clear"}


def _sig(key: str, level: str) -> SignalResult:
    return SignalResult(key, level, None, None, "", "store")


def test_신호별_집계는_켜짐과_꺼짐을_나누고_미판정은_뺀다():
    verdicts = [
        RegionIndustryVerdict("r1", "cafe", "red", 1, 1, (_sig("net_outflow", "strong"), _sig("saturation", "off")), _AT),
        RegionIndustryVerdict("r2", "cafe", "orange", 0, 1, (_sig("net_outflow", "on"), _sig("saturation", "unavailable")), _AT),
        RegionIndustryVerdict("r3", "cafe", "clear", 0, 0, (_sig("net_outflow", "off"), _sig("saturation", "off")), _AT),
        RegionIndustryVerdict("r1", "pub", "clear", 0, 0, (_sig("net_outflow", "off"), _sig("saturation", "on")), _AT),
    ]
    outcomes = [
        EntrantOutcome("r1", "cafe", 10, 8), EntrantOutcome("r2", "cafe", 10, 5),
        EntrantOutcome("r3", "cafe", 10, 2), EntrantOutcome("r1", "pub", 10, 3),
    ]
    buckets = summarize_signals(verdicts, outcomes)
    overall = {(b.signal_key, b.fired): b for b in buckets if b.industry_id is None}
    assert (overall[("net_outflow", True)].pairs, overall[("net_outflow", True)].opened, overall[("net_outflow", True)].closed) == (2, 20, 13)
    assert (overall[("net_outflow", False)].opened, overall[("net_outflow", False)].closed) == (20, 5)
    assert (overall[("saturation", True)].opened, overall[("saturation", False)].opened) == (10, 20)  # r2 미판정 제외
    cafe = {(b.signal_key, b.fired): b for b in buckets if b.industry_id == "cafe"}
    assert cafe[("net_outflow", True)].rate == 0.65 and cafe[("net_outflow", False)].rate == 0.2
    assert ("saturation", True) not in cafe


# --- 인터랙터 ---

class FakeRepository(RegionIndustryVerdictRepositoryPort):
    def upsert(self, verdicts):
        raise AssertionError("백테스트는 저장하지 않는다")

    def list_by_industry(self, industry_id):
        return []

    def list_by_region(self, region_code):
        return []

    def find(self, region_code, industry_id):
        return None

    def delete_other_industries(self, keep_industry_ids):
        raise AssertionError


class FakeStoreStats(StoreSignalStatsPort):
    def __init__(self):
        self.today = None

    def signal_stats(self, today):
        self.today = today
        regions = [f"r{i:02d}" for i in range(20)]
        return [
            StoreSignalStat(r, "cafe", start_store_count=100, opened_12m=10, closed_12m=10 + i, cohort_size=40,
                            cohort_survived=20, closed_3y_count=30, closed_3y_median_months=24.0)
            for i, r in enumerate(regions)
        ]


class FakeContext(RegionContextPort):
    def __init__(self):
        self.calls = []

    def latest_contexts(self, quarter_max=None):
        self.calls.append(("contexts", quarter_max))
        return [RegionContext(f"r{i:02d}", 10_000, "HH", "정체", quarter_max, 25.0, 27.0) for i in range(20)]

    def latest_store_counts(self, year_max=None):
        self.calls.append(("counts", year_max))
        return [LatestStoreCount(f"r{i:02d}", "cafe", 90) for i in range(20)]


class FakeCatalog(IndustryCatalogPort):
    def judged_industries(self):
        return [JudgedIndustry("cafe", "카페")]

    def named_industries(self, industry_ids):
        wanted = set(industry_ids)
        return [i for i in self.judged_industries() if i.industry_id in wanted]


class FakeRegions(RegionCatalogPort):
    def regions(self):
        return []


class FakeOutcomes(EntrantOutcomePort):
    def __init__(self):
        self.args = None

    def entrant_outcomes(self, as_of, entry_days, horizon_days):
        self.args = (as_of, entry_days, horizon_days)
        # 순유출이 큰 동(r19)일수록 폐업이 많게
        return [EntrantOutcome(f"r{i:02d}", "cafe", opened=10, closed_within=i // 2) for i in range(20)]


def test_백테스트는_상한을_넘겨_T시점_판정을_내고_결과와_조인한다():
    stats, ctx, outcomes = FakeStoreStats(), FakeContext(), FakeOutcomes()
    interactor = RegionIndustryVerdictInteractor(
        repository=FakeRepository(), store_stats=stats, region_context=ctx,
        industry_catalog=FakeCatalog(), region_catalog=FakeRegions(), entrant_outcomes=outcomes,
    )
    report = interactor.backtest(date(2022, 6, 30))

    assert stats.today == date(2022, 6, 30)
    assert ctx.calls == [("contexts", "20221"), ("counts", 2021)]
    assert outcomes.args == (date(2022, 6, 30), 365, 1095)
    assert report.as_of == date(2022, 6, 30)
    overall = {b.verdict_code: b for b in report.buckets if b.industry_id is None}
    # 순유출 상위 동만 orange(strong 1개) — 나머지는 clear. 폐업률은 orange 쪽이 높아야 한다
    assert overall["orange"].rate > overall["clear"].rate
    assert sum(b.pairs for b in overall.values()) == 20
    fired = {(b.signal_key, b.fired): b for b in report.signal_buckets if b.industry_id is None}
    assert fired[("net_outflow", True)].rate > fired[("net_outflow", False)].rate


# --- 재포함 게이트 ---

def _b(industry, code, pairs, opened, closed):
    return OutcomeBucket(industry, code, pairs, opened, closed)


def test_게이트는_경고_lift_1_10과_표본을_모두_넘어야_통과한다():
    buckets = [
        _b("convenience_store", "red", 3, 20, 8),
        _b("convenience_store", "orange", 100, 400, 80),
        _b("convenience_store", "clear", 80, 200, 30),
        _b("convenience_store", "insufficient", 50, 60, 30),  # 보류는 게이트에 안 들어간다
        _b(None, "clear", 1, 1, 1),
    ]
    gate = reinclusion_gate(buckets, "convenience_store", GATE_POLICIES["proxy"])
    assert gate.passed and gate.reason == "통과"
    assert gate.warn_lift == pytest.approx((88 / 420) / (30 / 200))
    assert (gate.warn_opened, gate.clear_opened, gate.warn_pairs, gate.clear_pairs) == (420, 200, 103, 80)


def test_게이트_경고_lift가_1_10_미만이면_미달이다():
    gate = reinclusion_gate([_b("x", "orange", 100, 400, 60), _b("x", "clear", 80, 200, 30)], "x", GATE_POLICIES["proxy"])
    assert not gate.passed and "경고 lift 1.00×" in gate.reason


def test_게이트_대리_원천은_개업_50곳_미만이면_미달이다():
    gate = reinclusion_gate([_b("x", "orange", 10, 49, 20), _b("x", "clear", 10, 200, 20)], "x", GATE_POLICIES["proxy"])
    assert not gate.passed and "개업" in gate.reason


def test_게이트_집계_원천은_동_30곳_미만이면_미달이다():
    gate = reinclusion_gate(
        [_b("x", "orange", 29, 5000, 900), _b("x", "clear", 200, 20000, 2000)], "x", GATE_POLICIES["aggregate"]
    )
    assert not gate.passed and "동×업종" in gate.reason


def test_게이트_경고_없음_판정이_없으면_lift를_못_내고_미달이다():
    gate = reinclusion_gate([_b("x", "orange", 50, 500, 50)], "x", GATE_POLICIES["proxy"])
    assert not gate.passed and gate.warn_lift is None and "계산 불가" in gate.reason


def test_게이트_경고_lift가_정확히_1_10이면_통과한다():
    gate = reinclusion_gate(
        [_b("x", "orange", 100, 1000, 550), _b("x", "clear", 80, 1000, 500)], "x", GATE_POLICIES["proxy"]
    )
    assert gate.passed and gate.warn_lift == pytest.approx(1.10)


@pytest.mark.parametrize("basis", ["proxy", "permit"])
def test_게이트_개업이_양쪽_정확히_50곳이면_통과한다(basis):
    gate = reinclusion_gate(
        [_b("x", "orange", 10, 50, 25), _b("x", "clear", 10, 50, 10)], "x", GATE_POLICIES[basis]
    )
    assert gate.passed


def test_게이트_집계_원천은_동x업종이_양쪽_정확히_30곳이면_통과한다():
    gate = reinclusion_gate(
        [_b("x", "orange", 30, 5000, 1200), _b("x", "clear", 30, 5000, 500)], "x", GATE_POLICIES["aggregate"]
    )
    assert gate.passed
