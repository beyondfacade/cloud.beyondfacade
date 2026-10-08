"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from functools import lru_cache

from apps.verdict.adapter.outbound.gateways.apt_trade_gateway import AptTradeGateway
from apps.verdict.adapter.outbound.gateways.commerce_aggregate_gateway import CommerceAggregateSignalData
from apps.verdict.adapter.outbound.gateways.entrant_outcome_gateway import EntrantOutcomeGateway
from apps.verdict.adapter.outbound.gateways.industry_catalog_gateway import IndustryCatalogGateway
from apps.verdict.adapter.outbound.gateways.region_catalog_gateway import RegionCatalogGateway
from apps.verdict.adapter.outbound.gateways.region_catalog_gateway_proxy import CachingRegionCatalogGatewayProxy
from apps.verdict.adapter.outbound.gateways.region_context_gateway import RegionContextGateway
from apps.verdict.adapter.outbound.gateways.store_signal_stats_gateway import StoreSignalStatsGateway
from apps.verdict.adapter.outbound.gateways.tobacco_convenience_gateway import TobaccoConvenienceSignalData
from apps.verdict.adapter.outbound.repositories.region_industry_verdict_repository import (
    SqlAlchemyRegionIndustryVerdictRepository,
)
from apps.verdict.adapter.outbound.repositories.region_industry_verdict_repository_proxy import (
    CachingRegionIndustryVerdictRepositoryProxy,
)
from apps.verdict.app.ports.input.region_industry_verdict_use_case import RegionIndustryVerdictUseCase
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    RegionCatalogPort,
    RegionIndustryVerdictRepositoryPort,
)
from apps.verdict.app.use_cases.industry_source import IndustrySource, TradeEnrichedSignalData
from apps.verdict.app.use_cases.region_industry_verdict_interactor import RegionIndustryVerdictInteractor
from apps.verdict.domain.services.profiles import AggregateProfile, TobaccoProxyProfile


@lru_cache
def _cached_repository() -> RegionIndustryVerdictRepositoryPort:
    """캐싱 Proxy가 상태를 가지므로 프로세스당 1개 — API 라우터와 agent의 VerdictFactsGateway가 공유한다.
    배치·백테스트 CLI도 같은 배선을 쓰므로 쓰기 메서드는 위임 뒤 캐시를 비운다."""
    return CachingRegionIndustryVerdictRepositoryProxy(SqlAlchemyRegionIndustryVerdictRepository())


@lru_cache
def _cached_region_catalog() -> RegionCatalogPort:
    return CachingRegionCatalogGatewayProxy(RegionCatalogGateway())


def get_region_industry_verdict_use_case() -> RegionIndustryVerdictUseCase:
    return RegionIndustryVerdictInteractor(
        repository=_cached_repository(),
        store_stats=StoreSignalStatsGateway(),
        region_context=RegionContextGateway(),
        industry_catalog=IndustryCatalogGateway(),
        region_catalog=_cached_region_catalog(),
        entrant_outcomes=EntrantOutcomeGateway(),
        # 업종별 원천 (업종 특화 신호 설계서 §4) — 판정 대상 여부는 EXCLUDED_INDUSTRIES가 따로 정한다
        sources={
            "convenience_store": IndustrySource(TobaccoProxyProfile(), TobaccoConvenienceSignalData()),
            "real_estate": IndustrySource(
                AggregateProfile(), TradeEnrichedSignalData(CommerceAggregateSignalData(("real_estate",)), AptTradeGateway())
            ),
        },
    )
