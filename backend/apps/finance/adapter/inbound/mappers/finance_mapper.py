"""Inbound Boundary Gate — schema ↔ dto 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.finance.adapter.inbound.api.schemas.finance_schema import (
    PrefillResponse,
    PrefillValueResponse,
    QuestionResponse,
    QuestionsRequest,
    QuestionsResponse,
    SimulateRequest,
    SimulateResponse,
)
from apps.finance.app.dtos.finance_dto import (
    FinanceInputDto,
    FinanceResultDto,
    PrefillDto,
    PrefillValueDto,
    QuestionDto,
    QuestionProfileDto,
    QuestionRequestDto,
)


def to_input_dto(request: SimulateRequest) -> FinanceInputDto:
    return FinanceInputDto(**request.model_dump())


def to_simulate_response(dto: FinanceResultDto) -> SimulateResponse:
    return SimulateResponse(**asdict(dto))


def _value(dto: PrefillValueDto) -> PrefillValueResponse:
    return PrefillValueResponse(value=dto.value, basis=dto.basis, caveat=dto.caveat, unit=dto.unit)


def to_prefill_response(dto: PrefillDto) -> PrefillResponse:
    return PrefillResponse(
        region_code=dto.region_code,
        industry_id=dto.industry_id,
        expected_monthly_revenue=_value(dto.expected_monthly_revenue),
        rent_per_m2=_value(dto.rent_per_m2),
        cost_ratio=_value(dto.cost_ratio),
        loan_rate=_value(dto.loan_rate),
    )


def to_questions_request_dto(request: QuestionsRequest) -> QuestionRequestDto:
    return QuestionRequestDto(
        input=to_input_dto(request.input),
        unconfirmed=tuple(request.unconfirmed),
        prefilled=tuple(request.prefilled),
        candidate_titles=tuple(request.candidate_titles),
        profile=QuestionProfileDto(**request.profile.model_dump()),
        change_reason=request.change_reason,
    )


def to_questions_response(dtos: list[QuestionDto]) -> QuestionsResponse:
    return QuestionsResponse(
        questions=[QuestionResponse(**asdict(dto)) for dto in dtos]
    )
