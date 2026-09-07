"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.store.adapter.outbound.gateways.industry_catalog_gateway import (
    IndustryCatalogGateway,
)
from apps.store.adapter.outbound.gateways.mois_permit_gateway import MoisPermitGateway
from apps.store.adapter.outbound.repositories.store_repository import (
    SqlAlchemyStoreRepository,
)
from apps.store.app.ports.input.store_use_case import StoreUseCase
from apps.store.app.use_cases.store_interactor import StoreInteractor


def get_store_use_case() -> StoreUseCase:
    return StoreInteractor(
        repository=SqlAlchemyStoreRepository(),
        gateway=MoisPermitGateway(),
        industry_catalog=IndustryCatalogGateway(),
    )
