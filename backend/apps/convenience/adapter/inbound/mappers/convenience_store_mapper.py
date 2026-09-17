"""Inbound Boundary Gate — dto → schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.convenience.adapter.inbound.api.schemas.convenience_store_schema import (
    ConvenienceRegionSummaryResponse,
    ConvenienceStoreMarkerResponse,
)
from apps.convenience.app.dtos.convenience_store_dto import (
    ConvenienceRegionSummaryDto,
    ConvenienceStoreDto,
)


def to_marker_response(dto: ConvenienceStoreDto) -> ConvenienceStoreMarkerResponse:
    return ConvenienceStoreMarkerResponse(**asdict(dto))


def to_summary_response(dto: ConvenienceRegionSummaryDto) -> ConvenienceRegionSummaryResponse:
    return ConvenienceRegionSummaryResponse(**asdict(dto))
