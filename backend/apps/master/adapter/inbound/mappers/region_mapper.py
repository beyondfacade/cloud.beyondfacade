"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.master.adapter.inbound.api.schemas.region_schema import RegionResponse
from apps.master.app.dtos.region_dto import RegionDto


def to_response(dto: RegionDto) -> RegionResponse:
    return RegionResponse(**asdict(dto))
