"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.shock.adapter.inbound.api.schemas.event_analog_schema import (
    EventAnalogReportResponse,
)
from apps.shock.app.dtos.event_analog_dto import EventAnalogReportDto


def to_response(dto: EventAnalogReportDto) -> EventAnalogReportResponse:
    return EventAnalogReportResponse(**asdict(dto))
