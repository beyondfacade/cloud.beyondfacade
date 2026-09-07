"""metric build 검증 — 연도별 지표 계산(폐업률·성장률·전년 0 가드)과 멱등성 (Fake 포트)."""

from apps.metric.app.dtos.region_industry_metric_dto import YearlyStoreStat
from apps.metric.app.ports.output.region_industry_metric_port import (
    IndustryCatalogPort,
    RegionIndustryMetricRepositoryPort,
    StoreStatsPort,
)
from apps.metric.app.use_cases.region_industry_metric_interactor import (
    RegionIndustryMetricInteractor,
)
from apps.metric.domain.entities.region_industry_metric_entity import (
    RegionIndustryMetric,
)


class FakeRepository(RegionIndustryMetricRepositoryPort):
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str, int], RegionIndustryMetric] = {}

    def upsert(self, metrics: list[RegionIndustryMetric]) -> int:
        for metric in metrics:
            self.rows[(metric.region_code, metric.industry_id, metric.year)] = metric
        return len(metrics)

    def list_by_industry_year(
        self, industry_id: str, year: int
    ) -> list[RegionIndustryMetric]:
        return sorted(
            (
                m
                for m in self.rows.values()
                if m.industry_id == industry_id and m.year == year
            ),
            key=lambda m: m.region_code,
        )

    def find(
        self, region_code: str, industry_id: str, year: int
    ) -> RegionIndustryMetric | None:
        return self.rows.get((region_code, industry_id, year))


class FakeStoreStats(StoreStatsPort):
    def __init__(self, stats: list[YearlyStoreStat]) -> None:
        self._stats = stats
        self.requested_years: list[int] | None = None

    def yearly_stats(self, years: list[int]) -> list[YearlyStoreStat]:
        self.requested_years = years
        return [s for s in self._stats if s.year in years]


class FakeIndustryCatalog(IndustryCatalogPort):
    def __init__(self, industry_ids: set[str]) -> None:
        self._industry_ids = industry_ids

    def exists(self, industry_id: str) -> bool:
        return industry_id in self._industry_ids


def _stat(year: int, store: int, opened: int, closed: int) -> YearlyStoreStat:
    return YearlyStoreStat(
        region_code="1168064000",
        industry_id="cafe",
        year=year,
        store_count=store,
        open_count=opened,
        close_count=closed,
    )


def _interactor(
    stats: list[YearlyStoreStat],
) -> tuple[RegionIndustryMetricInteractor, FakeRepository, FakeStoreStats]:
    repository = FakeRepository()
    store_stats = FakeStoreStats(stats)
    interactor = RegionIndustryMetricInteractor(
        repository=repository,
        store_stats=store_stats,
        industry_catalog=FakeIndustryCatalog({"cafe"}),
    )
    return interactor, repository, store_stats


def test_build_computes_rates_from_previous_year_store_count():
    interactor, repository, _ = _interactor(
        [_stat(2019, store=10, opened=1, closed=0), _stat(2020, store=11, opened=3, closed=2)]
    )
    interactor.build([2020])

    metric = repository.rows[("1168064000", "cafe", 2020)]
    assert metric.store_count == 11
    assert metric.open_count == 3
    assert metric.close_count == 2
    assert metric.closure_rate == 0.2  # 2 ÷ 전년 말 10
    assert metric.growth_rate == 0.1  # (3 − 2) ÷ 전년 말 10


def test_build_guards_rates_none_when_previous_year_zero():
    interactor, repository, _ = _interactor(
        [_stat(2019, store=0, opened=0, closed=0), _stat(2020, store=5, opened=5, closed=0)]
    )
    interactor.build([2020])

    metric = repository.rows[("1168064000", "cafe", 2020)]
    assert metric.closure_rate is None
    assert metric.growth_rate is None


def test_build_guards_rates_none_when_previous_year_missing():
    interactor, repository, _ = _interactor([_stat(2020, store=5, opened=5, closed=0)])
    interactor.build([2020])

    metric = repository.rows[("1168064000", "cafe", 2020)]
    assert metric.closure_rate is None
    assert metric.growth_rate is None


def test_build_requests_previous_year_but_upserts_target_years_only():
    interactor, repository, store_stats = _interactor(
        [_stat(2018, store=3, opened=0, closed=0), _stat(2019, store=4, opened=1, closed=0)]
    )
    interactor.build([2019, 2020])

    assert store_stats.requested_years == [2018, 2019, 2020]
    assert set(repository.rows) == {("1168064000", "cafe", 2019)}  # 보조 연도 2018 미적재
    assert repository.rows[("1168064000", "cafe", 2019)].closure_rate == 0.0


def test_build_is_idempotent():
    interactor, repository, _ = _interactor(
        [_stat(2019, store=10, opened=1, closed=0), _stat(2020, store=11, opened=3, closed=2)]
    )
    first = interactor.build([2019, 2020])
    snapshot = dict(repository.rows)
    second = interactor.build([2019, 2020])

    assert first == second
    assert repository.rows == snapshot
