"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.convenience.adapter.outbound.gateways.region_catalog_gateway import (
    RegionCatalogGateway,
)
from apps.convenience.adapter.outbound.repositories.convenience_store_repository import (
    SqlAlchemyConvenienceStoreRepository,
)
from apps.convenience.app.ports.input.convenience_store_use_case import (
    ConvenienceStoreQueryUseCase,
)
from apps.convenience.app.use_cases.convenience_store_interactor import (
    ConvenienceStoreQueryInteractor,
)


def get_convenience_store_query_use_case() -> ConvenienceStoreQueryUseCase:
    return ConvenienceStoreQueryInteractor(
        repository=SqlAlchemyConvenienceStoreRepository(), region_catalog=RegionCatalogGateway()
    )
