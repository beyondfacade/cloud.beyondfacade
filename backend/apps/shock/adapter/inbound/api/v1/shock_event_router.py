from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.shock.adapter.inbound.api.schemas.shock_event_schema import (
    ShockEventResponse,
)
from apps.shock.adapter.inbound.mappers.shock_event_mapper import to_response
from apps.shock.app.ports.input.shock_event_use_case import ShockEventUseCase
from apps.shock.dependencies.shock_event_dependencies import get_shock_event_use_case

router = APIRouter(prefix="/shocks", tags=["shock"])

_LIMIT_MAX = 100


@router.get("/myself", response_model=ShockEventResponse)
def myself(
    use_case: ShockEventUseCase = Depends(get_shock_event_use_case),
) -> ShockEventResponse:
    return to_response(use_case.myself())


@router.get("", response_model=list[ShockEventResponse])
def list_events(
    industry: str | None = None,
    limit: int = 50,
    use_case: ShockEventUseCase = Depends(get_shock_event_use_case),
) -> list[ShockEventResponse] | JSONResponse:
    if limit < 1 or limit > _LIMIT_MAX:
        # 에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_LIMIT",
                    "message": f"limit은 1~{_LIMIT_MAX} 사이여야 합니다: {limit}",
                }
            },
        )
    return [to_response(dto) for dto in use_case.list_events(industry, limit)]
