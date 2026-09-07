"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.shock.adapter.inbound.api.schemas.shock_event_schema import (
    ShockEventResponse,
)
from apps.shock.app.dtos.shock_event_dto import ShockEventDto


def to_response(dto: ShockEventDto) -> ShockEventResponse:
    return ShockEventResponse(**asdict(dto))
