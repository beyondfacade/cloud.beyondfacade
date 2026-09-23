from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.intent.adapter.inbound.api.schemas.intent_schema import IntentRequest, IntentResponse
from apps.intent.adapter.inbound.mappers.intent_mapper import to_response
from apps.intent.app.ports.input.intent_use_case import IntentUseCase
from apps.intent.dependencies.intent_dependencies import get_intent_use_case
from apps.intent.domain.errors import (
    IndustryNotFoundError,
    IntentTextEmptyError,
    RegionNotFoundError,
)

router = APIRouter(prefix="/intent", tags=["intent"])


def _error(status: int, code: str, message: str) -> JSONResponse:
    """에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)."""
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@router.get("/myself", response_model=IntentResponse)
def myself(use_case: IntentUseCase = Depends(get_intent_use_case)) -> IntentResponse:
    return to_response(use_case.myself())


@router.post("", response_model=IntentResponse)
def extract(
    request: IntentRequest, use_case: IntentUseCase = Depends(get_intent_use_case)
) -> IntentResponse | JSONResponse:
    """문장이 오면 파싱, 코드 쌍이 오면 진단만. 파싱 실패는 실패가 아니다 — C유형 200."""
    try:
        if request.text is not None:
            return to_response(use_case.parse(request.text))
        if request.region_code and request.industry_id:
            return to_response(use_case.diagnose(request.region_code, request.industry_id))
        raise IntentTextEmptyError()
    except IntentTextEmptyError:
        return _error(400, "INTENT_TEXT_EMPTY", "문장 또는 region_code+industry_id가 필요합니다")
    except RegionNotFoundError as error:
        return _error(404, "REGION_NOT_FOUND", f"알 수 없는 region_code: {error}")
    except IndustryNotFoundError as error:
        return _error(404, "INDUSTRY_NOT_FOUND", f"지원하지 않는 industry: {error}")
