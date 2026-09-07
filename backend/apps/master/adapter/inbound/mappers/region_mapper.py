"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.master.adapter.inbound.api.schemas.region_schema import (
    RegionResponse,
    RegionSummaryResponse,
)
from apps.master.app.dtos.region_dto import RegionDto, RegionSummaryDto


def to_response(dto: RegionDto) -> RegionResponse:
    return RegionResponse(**asdict(dto))


def to_summary_response(dto: RegionSummaryDto) -> RegionSummaryResponse:
    return RegionSummaryResponse(**asdict(dto))  # 중첩 카드는 pydantic이 dict→모델 변환
