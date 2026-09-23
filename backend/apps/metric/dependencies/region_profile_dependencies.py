"""Composition Root (DIP) — 파생 지표 Port에 Adapter를 주입한다."""

from apps.metric.adapter.outbound.gateways.hour_gap_source_gateways import (
    RegionFootfallHourGateway,
    RegionIndustryHourSalesGateway,
)
from apps.metric.adapter.outbound.gateways.neighborhood_observation_gateway import (
    NeighborhoodObservationGateway,
)
from apps.metric.adapter.outbound.repositories.region_industry_hour_gap_repository import (
    SqlAlchemyRegionIndustryHourGapRepository,
)
from apps.metric.adapter.outbound.repositories.region_profile_repository import (
    SqlAlchemyRegionProfileRepository,
)
from apps.metric.app.ports.input.region_industry_hour_gap_use_case import (
    RegionIndustryHourGapUseCase,
)
from apps.metric.app.ports.input.region_profile_use_case import RegionProfileUseCase
from apps.metric.app.use_cases.region_industry_hour_gap_interactor import (
    RegionIndustryHourGapInteractor,
)
from apps.metric.app.use_cases.region_profile_interactor import RegionProfileInteractor


def get_region_profile_use_case() -> RegionProfileUseCase:
    return RegionProfileInteractor(
        repository=SqlAlchemyRegionProfileRepository(),
        observations=NeighborhoodObservationGateway(),
    )


def get_region_industry_hour_gap_use_case() -> RegionIndustryHourGapUseCase:
    return RegionIndustryHourGapInteractor(
        repository=SqlAlchemyRegionIndustryHourGapRepository(),
        footfall=RegionFootfallHourGateway(),
        sales=RegionIndustryHourSalesGateway(),
    )
