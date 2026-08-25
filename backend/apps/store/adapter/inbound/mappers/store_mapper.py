"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.store.adapter.inbound.api.schemas.store_schema import StoreResponse
from apps.store.app.dtos.store_dto import StoreDto


def to_response(dto: StoreDto) -> StoreResponse:
    return StoreResponse(**asdict(dto))
