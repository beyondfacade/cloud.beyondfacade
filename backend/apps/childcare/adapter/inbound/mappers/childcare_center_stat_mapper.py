"""Inbound Boundary Gate — dto → schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.childcare.adapter.inbound.api.schemas.childcare_center_stat_schema import (
    ChildcareRegionSummaryResponse,
)
from apps.childcare.app.dtos.childcare_center_stat_dto import ChildcareRegionSummaryDto


def to_summary_response(dto: ChildcareRegionSummaryDto) -> ChildcareRegionSummaryResponse:
    return ChildcareRegionSummaryResponse(**asdict(dto))
