from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.funding.adapter.inbound.api.schemas.funding_program_schema import (
    FundingProgramResponse,
)
from apps.funding.adapter.inbound.mappers.funding_program_mapper import to_response
from apps.funding.app.ports.input.funding_program_use_case import FundingProgramUseCase
from apps.funding.dependencies.funding_program_dependencies import (
    get_funding_program_use_case,
)

router = APIRouter(prefix="/funding", tags=["funding"])

_LIMIT_MAX = 100


@router.get("/myself", response_model=FundingProgramResponse)
def myself(
    use_case: FundingProgramUseCase = Depends(get_funding_program_use_case),
) -> FundingProgramResponse:
    return to_response(use_case.myself())


@router.get("", response_model=list[FundingProgramResponse])
def list_open_programs(
    limit: int = 20,
    use_case: FundingProgramUseCase = Depends(get_funding_program_use_case),
) -> list[FundingProgramResponse] | JSONResponse:
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
    return [to_response(dto) for dto in use_case.list_open(limit)]
