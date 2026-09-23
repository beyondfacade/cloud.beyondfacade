"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.funding.adapter.inbound.api.schemas.funding_program_schema import (
    FundingCandidateListResponse,
    FundingCandidateResponse,
    FundingProgramResponse,
)
from apps.funding.app.dtos.funding_program_dto import (
    FundingCandidateListDto,
    FundingProgramDto,
)


def to_response(dto: FundingProgramDto) -> FundingProgramResponse:
    return FundingProgramResponse(**asdict(dto))


def to_candidate_list_response(dto: FundingCandidateListDto) -> FundingCandidateListResponse:
    return FundingCandidateListResponse(
        candidates=[
            FundingCandidateResponse(**asdict(item.program), why=item.why)
            for item in dto.candidates
        ],
        industry_id=dto.industry_id,
        external_funding_need=dto.external_funding_need,
        stage=dto.stage,
    )
