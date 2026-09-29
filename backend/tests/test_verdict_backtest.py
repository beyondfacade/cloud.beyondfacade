"""백테스트 — 직전 분기 라벨·집계(도메인)·인터랙터가 상한을 넘기고 결과와 조인하는지 (Fake 포트) (설계서 §13)."""

from datetime import date, datetime, timezone

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
from apps.verdict.domain.entities.region_industry_verdict_entity import RegionIndustryVerdict
from apps.verdict.domain.services.backtest import quarter_before, summarize

_AT = datetime(2026, 9, 29, tzinfo=timezone.utc)


def _v(region: str, industry: str, code: str) -> RegionIndustryVerdict:
    return RegionIndustryVerdict(region, industry, code, 0, 0, (), _AT)


def test_직전_분기_라벨():
    assert quarter_before(date(2022, 6, 30)) == "20221"
    assert quarter_before(date(2026, 1, 15)) == "20254"
    assert quarter_before(date(2024, 12, 31)) == "20243"


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
