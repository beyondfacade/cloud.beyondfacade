from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.verdict.adapter.inbound.api.schemas.region_industry_verdict_schema import (
    RegionIndustryVerdictResponse,
    VerdictValueResponse,
)
from apps.verdict.adapter.inbound.mappers.region_industry_verdict_mapper import to_response, to_value_response
from apps.verdict.app.ports.input.region_industry_verdict_use_case import RegionIndustryVerdictUseCase
from apps.verdict.dependencies.region_industry_verdict_dependencies import get_region_industry_verdict_use_case
from apps.verdict.domain.errors import IndustryNotFoundError

router = APIRouter(prefix="/verdicts", tags=["verdicts"])


def _not_found(code: str, message: str) -> JSONResponse:
    """에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)."""
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})


@router.get("/myself", response_model=RegionIndustryVerdictResponse)
def myself(use_case: RegionIndustryVerdictUseCase = Depends(get_region_industry_verdict_use_case)):
    return to_response(use_case.myself())


@router.get("", response_model=list[VerdictValueResponse])
def list_verdict_values(
    industry: str,
    use_case: RegionIndustryVerdictUseCase = Depends(get_region_industry_verdict_use_case),
) -> list[VerdictValueResponse] | JSONResponse:
    try:
        values = use_case.list_verdict_values(industry)
    except IndustryNotFoundError:
        return _not_found("INDUSTRY_NOT_FOUND", f"판정 대상 업종이 아닙니다: {industry}")
    return [to_value_response(v) for v in values]


# `/{region_code}`는 ""·/myself 뒤에 선언한다 — 앞에 두면 "myself"를 동 코드로 먹는다.
@router.get("/{region_code}", response_model=RegionIndustryVerdictResponse)
def find_verdict(
    region_code: str,
    industry: str,
    use_case: RegionIndustryVerdictUseCase = Depends(get_region_industry_verdict_use_case),
) -> RegionIndustryVerdictResponse | JSONResponse:
    try:
        dto = use_case.find(region_code, industry)
    except IndustryNotFoundError:
        return _not_found("INDUSTRY_NOT_FOUND", f"판정 대상 업종이 아닙니다: {industry}")
    if dto is None:
        return _not_found("VERDICT_NOT_FOUND", f"판정이 없습니다: {region_code} × {industry}")
    return to_response(dto)
