from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.master.adapter.inbound.api.schemas.region_schema import (
    RegionResponse,
    RegionSummaryResponse,
)
from apps.master.adapter.inbound.mappers.region_mapper import (
    to_response,
    to_summary_response,
)
from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.dependencies.region_dependencies import get_region_use_case
from apps.master.domain.errors import RegionNotFoundError

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("/myself", response_model=RegionResponse)
def myself(
    use_case: RegionUseCase = Depends(get_region_use_case),
) -> RegionResponse:
    return to_response(use_case.myself())


@router.get("/geojson")
def geojson(
    use_case: RegionUseCase = Depends(get_region_use_case),
) -> dict:
    return use_case.geojson()


@router.get("/{region_code}/summary", response_model=RegionSummaryResponse)
def summary(
    region_code: str,
    industry: str,
    use_case: RegionUseCase = Depends(get_region_use_case),
) -> RegionSummaryResponse | JSONResponse:
    try:
        dto = use_case.summary(region_code, industry)
    except RegionNotFoundError:
        # 에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "REGION_NOT_FOUND",
                    "message": f"알 수 없는 region_code: {region_code}",
                }
            },
        )
    return to_summary_response(dto)
