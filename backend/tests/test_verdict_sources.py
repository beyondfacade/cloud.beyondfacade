"""업종별 원천 레지스트리 — 인터랙터가 업종마다 등록된 원천·프로필로 판정하고 basis를 싣는다 (업종 특화 신호 설계서 §4)."""

from datetime import date

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
    IndustrySignalDataPort,
    RegionCatalogPort,
    RegionContextPort,
    RegionIndustryVerdictRepositoryPort,
    StoreSignalStatsPort,
)
from apps.verdict.app.use_cases.industry_source import IndustrySource
from apps.verdict.app.use_cases.region_industry_verdict_interactor import RegionIndustryVerdictInteractor
from apps.verdict.domain.services.profiles import AggregateProfile, TobaccoProxyProfile

_REGIONS = [f"r{i:02d}" for i in range(20)]
_NAMES = {"korean_food": "한식", "convenience_store": "편의점", "real_estate": "부동산중개업"}


def _stat(region, industry, closed_12m, gap=(0, 0)):
    return StoreSignalStat(
        region, industry, start_store_count=100, opened_12m=10, closed_12m=closed_12m, cohort_size=0,
        cohort_survived=0, closed_3y_count=0, closed_3y_median_months=None, gap_candidates=gap[0], gap_blocked=gap[1],
    )


class FakeRepository(RegionIndustryVerdictRepositoryPort):
    def upsert(self, verdicts):
        return len(verdicts)

    def list_by_industry(self, industry_id):
        return []

    def list_by_region(self, region_code):
        return []

    def find(self, region_code, industry_id):
        return None

    def delete_other_industries(self, keep_industry_ids):
        return 0


class FakeStoreStats(StoreSignalStatsPort):
    """인허가 원천 — 편의점 행도 일부러 돌려준다(편의점 판정에 쓰이면 안 된다)."""

    def signal_stats(self, today):
        return [_stat(r, "korean_food", 10 + i) for i, r in enumerate(_REGIONS)] + [
            _stat(r, "convenience_store", 90) for r in _REGIONS
        ]


class FakeContext(RegionContextPort):
    def latest_contexts(self, quarter_max=None):
        return [RegionContext(r, 10_000, "HH", "정체", "20262", 25.0, 27.0) for r in _REGIONS]

    def latest_store_counts(self, year_max=None):
        return [LatestStoreCount(r, "korean_food", 90) for r in _REGIONS]


class FakeData(IndustrySignalDataPort):
    def __init__(self, industry_id):
        self.industry_id = industry_id
        self.calls = []

    def signal_stats(self, today):
        self.calls.append(("stats", today))
        return [_stat(r, self.industry_id, 10 + i, gap=(100, 50 + i)) for i, r in enumerate(_REGIONS)]

    def store_counts(self, year_max, quarter_max):
        self.calls.append(("counts", year_max, quarter_max))
        return [LatestStoreCount(r, self.industry_id, 20 + i) for i, r in enumerate(_REGIONS)]

    def entrant_outcomes(self, as_of, entry_days, horizon_days):
        self.calls.append(("outcomes", as_of))
        return [EntrantOutcome(r, self.industry_id, opened=100, closed_within=i) for i, r in enumerate(_REGIONS)]


class FakeCatalog(IndustryCatalogPort):
    def __init__(self, judged):
        self.judged = judged

    def judged_industries(self):
        return list(self.judged)

    def named_industries(self, industry_ids):
        return [JudgedIndustry(i, _NAMES[i]) for i in industry_ids]


class FakeOutcomes(EntrantOutcomePort):
    """인허가 원천 결과 — 부동산 행(999)도 섞는다(집계 원천 업종에 쓰이면 안 된다)."""

    def entrant_outcomes(self, as_of, entry_days, horizon_days):
        return [EntrantOutcome(r, "korean_food", 10, 3) for r in _REGIONS] + [
            EntrantOutcome(r, "real_estate", 999, 999) for r in _REGIONS
        ]


class FakeRegions(RegionCatalogPort):
    def regions(self):
        return []


def _interactor(judged, sources):
    return RegionIndustryVerdictInteractor(
        repository=FakeRepository(), store_stats=FakeStoreStats(), region_context=FakeContext(),
        industry_catalog=FakeCatalog(judged), region_catalog=FakeRegions(), entrant_outcomes=FakeOutcomes(),
        sources=sources,
    )


def test_등록된_업종은_자기_원천과_프로필로_판정하고_basis를_싣는다():
    data = FakeData("convenience_store")
    interactor = _interactor(
        [JudgedIndustry("korean_food", "한식"), JudgedIndustry("convenience_store", "편의점")],
        {"convenience_store": IndustrySource(TobaccoProxyProfile(), data)},
    )
    verdicts = {(v.region_code, v.industry_id): v for v in interactor.compute(date(2026, 9, 29))}
    conv = verdicts[("r19", "convenience_store")]
    assert conv.basis == "proxy"
    assert [s.key for s in conv.signals] == [
        "net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking", "tobacco_gap",
    ]
    assert conv.signals[0].source == "tobacco"
    assert conv.signals[0].value == pytest.approx((29 - 10) / 100)  # 인허가 원천의 편의점 행(90)이 아니라 원천 데이터 값
    assert conv.signals[5].value == pytest.approx(69 / 100)
    korean = verdicts[("r19", "korean_food")]
    assert korean.basis == "permit" and korean.signals[0].source == "store"


def test_원천은_업종이_여럿이어도_한_번만_읽는다():
    data = FakeData("convenience_store")
    interactor = _interactor(
        [JudgedIndustry("convenience_store", "편의점"), JudgedIndustry("convenience_store", "편의점")],
        {"convenience_store": IndustrySource(TobaccoProxyProfile(), data)},
    )
    interactor.compute(date(2026, 9, 29))
    assert data.calls == [("stats", date(2026, 9, 29)), ("counts", None, None)]


def test_집계_원천_백테스트는_상한을_넘기고_전체_합산에서_빠진다():
    data = FakeData("real_estate")
    interactor = _interactor([JudgedIndustry("korean_food", "한식")], {"real_estate": IndustrySource(AggregateProfile(), data)})
    report = interactor.backtest(date(2022, 6, 30), industry_ids=["real_estate"])
    assert ("counts", 2021, "20221") in data.calls and ("outcomes", date(2022, 6, 30)) in data.calls
    assert report.industry_basis == (("real_estate", "aggregate"),)
    assert all(b.industry_id == "real_estate" for b in report.buckets)  # 전체(None) 버킷 없음
    assert sum(b.opened for b in report.buckets) == 100 * 20  # 인허가 원천의 부동산 결과(999)는 버린다
    assert {b.signal_key for b in report.signal_buckets} <= {"closure_rate", "saturation", "shrinking"}


def test_등록됐지만_판정_대상이_아닌_업종은_원천을_건드리지_않는다():
    """제외 업종의 원천을 등록해도 compute()가 그 업종을 targets에 안 넣으면 원천은 아예 안 읽는다
    (배선 주석이 약속하는 비용 0 보장, Important 리뷰 §5)."""
    data = FakeData("convenience_store")
    interactor = _interactor(
        [JudgedIndustry("korean_food", "한식")],  # convenience_store는 judged에 없음
        {"convenience_store": IndustrySource(TobaccoProxyProfile(), data)},
    )
    verdicts = interactor.compute(date(2026, 9, 29))
    assert data.calls == []
    assert all(v.industry_id != "convenience_store" for v in verdicts)


def test_등록되지_않은_업종은_기존_인허가_원천을_쓰고_전체_합산에_들어간다():
    report = _interactor([JudgedIndustry("korean_food", "한식")], {}).backtest(date(2022, 6, 30))
    assert report.industry_basis == (("korean_food", "permit"),)
    assert any(b.industry_id is None for b in report.buckets)
