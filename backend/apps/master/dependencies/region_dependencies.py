"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from functools import lru_cache

from apps.master.adapter.outbound.gateways.boundary_file_reader import (
    BoundaryFileReader,
)
from apps.master.adapter.outbound.gateways.metric_summary_gateway import (
    MetricSummaryGateway,
)
from apps.master.adapter.outbound.repositories.region_repository import (
    SqlAlchemyRegionRepository,
)
from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.app.use_cases.region_interactor import RegionInteractor
from apps.master.app.use_cases.region_use_case_proxy import CachingRegionUseCaseProxy


@lru_cache
def get_region_use_case() -> RegionUseCase:
    """캐싱 Proxy가 상태를 가지므로 프로세스당 1개 인스턴스를 공유한다."""
    return CachingRegionUseCaseProxy(
        RegionInteractor(
            repository=SqlAlchemyRegionRepository(),
            boundary_reader=BoundaryFileReader(),
            metric_summary=MetricSummaryGateway(),
        )
    )
