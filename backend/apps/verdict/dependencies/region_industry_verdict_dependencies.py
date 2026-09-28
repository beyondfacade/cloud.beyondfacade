"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.verdict.adapter.outbound.gateways.industry_catalog_gateway import IndustryCatalogGateway
from apps.verdict.adapter.outbound.gateways.region_context_gateway import RegionContextGateway
from apps.verdict.adapter.outbound.gateways.store_signal_stats_gateway import StoreSignalStatsGateway
from apps.verdict.adapter.outbound.repositories.region_industry_verdict_repository import (
    SqlAlchemyRegionIndustryVerdictRepository,
)
from apps.verdict.app.ports.input.region_industry_verdict_use_case import RegionIndustryVerdictUseCase
from apps.verdict.app.use_cases.region_industry_verdict_interactor import RegionIndustryVerdictInteractor


def get_region_industry_verdict_use_case() -> RegionIndustryVerdictUseCase:
    return RegionIndustryVerdictInteractor(
        repository=SqlAlchemyRegionIndustryVerdictRepository(),
        store_stats=StoreSignalStatsGateway(),
        region_context=RegionContextGateway(),
        industry_catalog=IndustryCatalogGateway(),
    )
