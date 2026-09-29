"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.verdict.adapter.inbound.api.schemas.region_industry_verdict_schema import (
    AlternativeIndustryResponse,
    AlternativeRegionResponse,
    RegionIndustryVerdictResponse,
    SignalResultResponse,
    VerdictAlternativesResponse,
    VerdictValueResponse,
)
from apps.verdict.app.dtos.region_industry_verdict_dto import (
    RegionIndustryVerdictDto,
    VerdictAlternativesDto,
    VerdictValueDto,
)


def to_response(dto: RegionIndustryVerdictDto) -> RegionIndustryVerdictResponse:
    return RegionIndustryVerdictResponse(
        region_code=dto.region_code, industry_id=dto.industry_id, verdict_code=dto.verdict_code,
        strong_count=dto.strong_count, on_count=dto.on_count,
        signals=[SignalResultResponse(**asdict(s)) for s in dto.signals], computed_at=dto.computed_at,
        basis=dto.basis,
    )


def to_value_response(dto: VerdictValueDto) -> VerdictValueResponse:
    return VerdictValueResponse(**asdict(dto))


def to_alternatives_response(dto: VerdictAlternativesDto) -> VerdictAlternativesResponse:
    return VerdictAlternativesResponse(
        region_code=dto.region_code, industry_id=dto.industry_id, neighborhood_type=dto.neighborhood_type,
        industries=[AlternativeIndustryResponse(**asdict(a)) for a in dto.industries],
        regions=[AlternativeRegionResponse(**asdict(a)) for a in dto.regions],
    )
