"""metric 단건 조회 검증 — find는 dto 또는 None (Fake 포트)."""

from apps.metric.app.dtos.region_industry_metric_dto import (
    RegionIndustryMetricDto,
    YearlyStoreStat,
)
from apps.metric.app.ports.output.region_industry_metric_port import (
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
    def __init__(self, metrics: list[RegionIndustryMetric]) -> None:
        self._metrics = metrics

    def upsert(self, metrics: list[RegionIndustryMetric]) -> int:
        raise NotImplementedError

    def find(
        self, region_code: str, industry_id: str, year: int
    ) -> RegionIndustryMetric | None:
        return next(
            (
                m
                for m in self._metrics
                if (m.region_code, m.industry_id, m.year)
                == (region_code, industry_id, year)
            ),
            None,
        )


class FakeStoreStats(StoreStatsPort):
    def yearly_stats(self, years: list[int]) -> list[YearlyStoreStat]:
        return []


def _metric(region_code: str, closure_rate: float | None) -> RegionIndustryMetric:
    return RegionIndustryMetric(
        region_code=region_code,
        industry_id="cafe",
        year=2025,
        store_count=10,
        open_count=1,
        close_count=1,
        closure_rate=closure_rate,
        growth_rate=None,
    )


def _interactor(metrics: list[RegionIndustryMetric]) -> RegionIndustryMetricInteractor:
    return RegionIndustryMetricInteractor(
        repository=FakeRepository(metrics),
        store_stats=FakeStoreStats(),
    )


def test_find_returns_dto_or_none():
    interactor = _interactor([_metric("1168064000", 0.1)])
    dto = interactor.find("1168064000", "cafe", 2025)
    assert isinstance(dto, RegionIndustryMetricDto)
    assert dto.closure_rate == 0.1
    assert interactor.find("1111051500", "cafe", 2025) is None
