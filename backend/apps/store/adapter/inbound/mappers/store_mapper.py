"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.store.adapter.inbound.api.schemas.store_schema import (
    StoreMarkerResponse,
    StoreResponse,
)
from apps.store.app.dtos.store_dto import StoreDto


def to_response(dto: StoreDto) -> StoreResponse:
    return StoreResponse(**asdict(dto))


def to_marker_response(dto: StoreDto) -> StoreMarkerResponse:
    return StoreMarkerResponse(
        store_id=dto.store_id,
        name=dto.name,
        lat=dto.lat,
        lng=dto.lng,
        status_name=dto.status_name,
        open_date=dto.open_date,
    )
