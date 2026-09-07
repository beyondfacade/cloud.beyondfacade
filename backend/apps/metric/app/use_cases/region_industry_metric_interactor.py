from collections.abc import Callable
from dataclasses import asdict

from apps.metric.app.dtos.region_industry_metric_dto import (
    MetricValueDto,
    RegionIndustryMetricDto,
)
from apps.metric.app.ports.input.region_industry_metric_use_case import (
    RegionIndustryMetricUseCase,
)
from apps.metric.app.ports.output.region_industry_metric_port import (
    IndustryCatalogPort,
    RegionIndustryMetricRepositoryPort,
    StoreStatsPort,
)
from apps.metric.domain.entities.region_industry_metric_entity import (
    RegionIndustryMetric,
)
from apps.metric.domain.errors import IndustryNotFoundError, MetricNotFoundError

# Strategy (GoF) — metric 이름 → 값 추출. if/elif 분기 대신 테이블 디스패치
_METRIC_EXTRACTORS: dict[str, Callable[[RegionIndustryMetric], float | int | None]] = {
    "store_count": lambda m: m.store_count,
    "closure_rate": lambda m: m.closure_rate,
    "growth_rate": lambda m: m.growth_rate,
}


def _rate(numerator: int, prev_store_count: int) -> float | None:
    """전년 말 점포 수 대비 비율 — 전년 0(또는 전년 집계 부재)이면 None."""
    if prev_store_count == 0:
        return None
    return numerator / prev_store_count


class RegionIndustryMetricInteractor(RegionIndustryMetricUseCase):
    def __init__(
        self,
        repository: RegionIndustryMetricRepositoryPort,
        store_stats: StoreStatsPort,
        industry_catalog: IndustryCatalogPort,
    ) -> None:
        self._repository = repository
        self._store_stats = store_stats
        self._industry_catalog = industry_catalog

    def myself(self) -> RegionIndustryMetricDto:
        return RegionIndustryMetricDto(
            region_code="myself",
            industry_id="cafe",
            year=2026,
            store_count=1,
            open_count=1,
            close_count=0,
            closure_rate=None,
            growth_rate=None,
        )

    def build(self, years: list[int]) -> int:
        # 첫 대상 연도의 비율 계산에 전년 말 store_count가 필요해 보조 연도 1개를 함께 집계
        stats = self._store_stats.yearly_stats([min(years) - 1, *years])
        by_key = {(s.region_code, s.industry_id, s.year): s for s in stats}
        target_years = set(years)
        metrics = []
        for stat in stats:
            if stat.year not in target_years:
                continue  # 보조 연도는 적재하지 않는다
            prev = by_key.get((stat.region_code, stat.industry_id, stat.year - 1))
            prev_store_count = prev.store_count if prev else 0
            metrics.append(
                RegionIndustryMetric(
                    region_code=stat.region_code,
                    industry_id=stat.industry_id,
                    year=stat.year,
                    store_count=stat.store_count,
                    open_count=stat.open_count,
                    close_count=stat.close_count,
                    closure_rate=_rate(stat.close_count, prev_store_count),
                    growth_rate=_rate(
                        stat.open_count - stat.close_count, prev_store_count
                    ),
                )
            )
        return self._repository.upsert(metrics)

    def list_metric_values(
        self, industry_id: str, metric: str, year: int
    ) -> list[MetricValueDto]:
        extractor = _METRIC_EXTRACTORS.get(metric)
        if extractor is None:
            raise MetricNotFoundError(metric)
        if not self._industry_catalog.exists(industry_id):
            raise IndustryNotFoundError(industry_id)
        return [
            MetricValueDto(region_code=entity.region_code, value=float(value))
            for entity in self._repository.list_by_industry_year(industry_id, year)
            if (value := extractor(entity)) is not None
        ]

    def find(
        self, region_code: str, industry_id: str, year: int
    ) -> RegionIndustryMetricDto | None:
        entity = self._repository.find(region_code, industry_id, year)
        if entity is None:
            return None
        return RegionIndustryMetricDto(**asdict(entity))
