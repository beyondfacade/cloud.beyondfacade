"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.funding.adapter.inbound.api.schemas.funding_program_schema import (
    FundingProgramResponse,
)
from apps.funding.app.dtos.funding_program_dto import FundingProgramDto


def to_response(dto: FundingProgramDto) -> FundingProgramResponse:
    return FundingProgramResponse(**asdict(dto))
