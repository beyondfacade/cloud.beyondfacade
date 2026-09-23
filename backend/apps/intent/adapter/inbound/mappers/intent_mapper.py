"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.intent.adapter.inbound.api.schemas.intent_schema import (
    DiagnosisResponse,
    IntentResponse,
    RegionCandidateResponse,
)
from apps.intent.app.dtos.intent_dto import IntentResultDto


def to_response(dto: IntentResultDto) -> IntentResponse:
    return IntentResponse(
        intent_type=dto.intent_type,
        region_code=dto.region_code,
        region_name=dto.region_name,
        district_code=dto.district_code,
        industry_id=dto.industry_id,
        budget_krw=dto.budget_krw,
        missing=dto.missing,
        candidates=[RegionCandidateResponse(**asdict(c)) for c in dto.candidates],
        diagnosis=None if dto.diagnosis is None else DiagnosisResponse(**asdict(dto.diagnosis)),
        source=dto.source,
    )
