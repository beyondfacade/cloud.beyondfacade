"""Inbound Boundary Gate — dto ↔ schema 변환."""

from dataclasses import asdict

from apps.admin.adapter.inbound.api.schemas.access_event_schema import (
    AccessEventPageResponse,
    SecurityOverviewResponse,
)
from apps.admin.app.dtos.access_event_dto import AccessEventPageDto, SecurityOverviewDto


def to_overview_response(dto: SecurityOverviewDto) -> SecurityOverviewResponse:
    return SecurityOverviewResponse.model_validate(asdict(dto))


def to_event_page_response(dto: AccessEventPageDto) -> AccessEventPageResponse:
    return AccessEventPageResponse.model_validate(asdict(dto))
