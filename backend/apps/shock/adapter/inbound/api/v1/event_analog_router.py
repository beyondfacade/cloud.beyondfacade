from fastapi import APIRouter, Depends

from apps.shock.adapter.inbound.api.schemas.event_analog_schema import (
    EventAnalogReportResponse,
)
from apps.shock.adapter.inbound.mappers.event_analog_mapper import to_response
from apps.shock.app.ports.input.event_analog_use_case import EventAnalogUseCase
from apps.shock.dependencies.event_analog_dependencies import get_event_analog_use_case

router = APIRouter(prefix="/shocks/analogs", tags=["shock"])


@router.get("/myself", response_model=EventAnalogReportResponse)
def myself(
    use_case: EventAnalogUseCase = Depends(get_event_analog_use_case),
) -> EventAnalogReportResponse:
    return to_response(use_case.myself())


@router.get("", response_model=EventAnalogReportResponse)
def analogs(
    industry: str,
    question: str | None = None,
    use_case: EventAnalogUseCase = Depends(get_event_analog_use_case),
) -> EventAnalogReportResponse:
    return to_response(use_case.analogs(industry, question))
