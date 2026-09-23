from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.finance.adapter.inbound.api.schemas.finance_schema import (
    PrefillResponse,
    QuestionsRequest,
    QuestionsResponse,
    SimulateRequest,
    SimulateResponse,
)
from apps.finance.adapter.inbound.mappers.finance_mapper import (
    to_input_dto,
    to_prefill_response,
    to_questions_request_dto,
    to_questions_response,
    to_simulate_response,
)
from apps.finance.app.ports.input.finance_use_case import FinanceUseCase
from apps.finance.dependencies.finance_dependencies import get_finance_use_case
from apps.finance.domain.errors import IndustryNotFoundError, RegionNotFoundError

router = APIRouter(prefix="/finance", tags=["finance"])


def _not_found(code: str, message: str) -> JSONResponse:
    """에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)."""
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})


@router.get("/myself", response_model=SimulateResponse)
def myself(use_case: FinanceUseCase = Depends(get_finance_use_case)) -> SimulateResponse:
    """§12 배선 검증 — 하드코딩 입력이 엔진을 실제로 통과해 돌아온다."""
    return to_simulate_response(use_case.myself())


@router.post("/simulate", response_model=SimulateResponse)
def simulate(
    request: SimulateRequest, use_case: FinanceUseCase = Depends(get_finance_use_case)
) -> SimulateResponse:
    """서버가 계산한다. 입력 검증(음수·변동비율 ≥ 1)은 422."""
    return to_simulate_response(use_case.simulate(to_input_dto(request)))


@router.get("/prefill", response_model=PrefillResponse)
def prefill(
    region: str, industry: str, use_case: FinanceUseCase = Depends(get_finance_use_case)
) -> PrefillResponse | JSONResponse:
    """실측 프리필 — 값마다 출처와 단서. 매출 없는 조합은 404가 아니라 값 null."""
    try:
        return to_prefill_response(use_case.prefill(region, industry))
    except RegionNotFoundError:
        return _not_found("REGION_NOT_FOUND", f"알 수 없는 region_code: {region}")
    except IndustryNotFoundError:
        return _not_found("INDUSTRY_NOT_FOUND", f"지원하지 않는 industry: {industry}")


@router.post("/questions", response_model=QuestionsResponse)
def questions(
    request: QuestionsRequest, use_case: FinanceUseCase = Depends(get_finance_use_case)
) -> QuestionsResponse:
    """확인할 질문 초안 (설계서 §4). 계산 결과는 받지 않고 `input`으로 서버가 다시 계산한다."""
    return to_questions_response(use_case.questions(to_questions_request_dto(request)))
