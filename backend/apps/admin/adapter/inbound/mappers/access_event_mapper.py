"""Inbound Boundary Gate — dto ↔ schema 변환."""

from dataclasses import asdict

from apps.admin.adapter.inbound.api.schemas.access_event_schema import SecurityOverviewResponse
from apps.admin.app.dtos.access_event_dto import SecurityOverviewDto


def to_overview_response(dto: SecurityOverviewDto) -> SecurityOverviewResponse:
    return SecurityOverviewResponse.model_validate(asdict(dto))
