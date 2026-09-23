from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.funding.adapter.inbound.api.schemas.funding_program_schema import (
    FundingCandidateListResponse,
    FundingProgramResponse,
)
from apps.funding.adapter.inbound.mappers.funding_program_mapper import (
    to_candidate_list_response,
    to_response,
)
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


# `/{...}` 경로 변수가 없어 선언 순서는 무관하지만, 목록(`""`)과 구분되게 아래에 둔다
@router.get("/candidates", response_model=FundingCandidateListResponse)
def list_candidates(
    industry: str | None = None,
    need: int | None = None,
    stage: str | None = None,
    use_case: FundingProgramUseCase = Depends(get_funding_program_use_case),
) -> FundingCandidateListResponse:
    """서울 창업자에게 해당하는 미만료 공고 상위 8건 (설계서 §3).

    자격 확정이 아니다. `industry`·`need`는 필터에 쓰이지 않고 응답에 그대로 돌아간다 —
    공고에 업종·한도가 구조화돼 있지 않다.
    """
    return to_candidate_list_response(use_case.list_candidates(industry, need, stage))
