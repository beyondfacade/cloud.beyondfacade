"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.metric.adapter.outbound.gateways.industry_catalog_gateway import (
    IndustryCatalogGateway,
)
from apps.metric.adapter.outbound.gateways.store_stats_gateway import StoreStatsGateway
from apps.metric.adapter.outbound.repositories.region_industry_metric_repository import (
    SqlAlchemyRegionIndustryMetricRepository,
)
from apps.metric.app.ports.input.region_industry_metric_use_case import (
    RegionIndustryMetricUseCase,
)
from apps.metric.app.use_cases.region_industry_metric_interactor import (
    RegionIndustryMetricInteractor,
)


def get_region_industry_metric_use_case() -> RegionIndustryMetricUseCase:
    return RegionIndustryMetricInteractor(
        repository=SqlAlchemyRegionIndustryMetricRepository(),
        store_stats=StoreStatsGateway(),
        industry_catalog=IndustryCatalogGateway(),
    )
