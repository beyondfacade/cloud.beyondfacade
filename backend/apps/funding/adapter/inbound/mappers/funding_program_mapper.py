"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.funding.adapter.inbound.api.schemas.funding_program_schema import (
    FundingCandidateListResponse,
    FundingCandidateResponse,
    FundingProgramResponse,
    RateResponse,
    SupportGuideResponse,
    SupportItemResponse,
)
from apps.funding.app.dtos.funding_program_dto import (
    FundingCandidateListDto,
    FundingProgramDto,
    SupportGuideDto,
    SupportItemDto,
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


def _to_support_item(item: SupportItemDto) -> SupportItemResponse:
    return SupportItemResponse(
        **asdict(item.program),
        why=item.why,
        district_match=item.district_match,
        industry_match=item.industry_match,
    )


def to_support_guide_response(dto: SupportGuideDto) -> SupportGuideResponse:
    return SupportGuideResponse(
        region_code=dto.region_code,
        district_name=dto.district_name,
        industry_id=dto.industry_id,
        loans=[_to_support_item(item) for item in dto.loans],
        district=[_to_support_item(item) for item in dto.district],
        others=[_to_support_item(item) for item in dto.others],
        rates=[RateResponse(**asdict(rate)) for rate in dto.rates],
    )
