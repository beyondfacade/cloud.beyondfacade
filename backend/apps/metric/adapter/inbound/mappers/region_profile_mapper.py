"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.metric.adapter.inbound.api.schemas.region_profile_schema import (
    RegionProfileResponse,
)
from apps.metric.app.dtos.region_profile_dto import RegionProfileDto


def to_response(dto: RegionProfileDto) -> RegionProfileResponse:
    return RegionProfileResponse(**asdict(dto))
