from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.convenience.adapter.inbound.api.schemas.convenience_store_schema import (
    ConvenienceRegionSummaryResponse,
    ConvenienceStoreMarkerResponse,
)
from apps.convenience.adapter.inbound.mappers.convenience_store_mapper import (
    to_marker_response,
    to_summary_response,
)
from apps.convenience.app.ports.input.convenience_store_use_case import (
    ConvenienceStoreQueryUseCase,
)
from apps.convenience.dependencies.convenience_dependencies import (
    get_convenience_store_query_use_case,
)
from apps.convenience.domain.errors import RegionNotFoundError

router = APIRouter(prefix="/convenience-stores", tags=["convenience"])


def _region_not_found(region_code: str) -> JSONResponse:
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


@router.get("/myself", response_model=ConvenienceStoreMarkerResponse)
def myself(
    use_case: ConvenienceStoreQueryUseCase = Depends(get_convenience_store_query_use_case),
) -> ConvenienceStoreMarkerResponse:
    return to_marker_response(use_case.myself())


@router.get("", response_model=list[ConvenienceStoreMarkerResponse])
def list_stores(
    region: str,
    use_case: ConvenienceStoreQueryUseCase = Depends(get_convenience_store_query_use_case),
) -> list[ConvenienceStoreMarkerResponse] | JSONResponse:
    try:
        stores = use_case.list_stores(region)
    except RegionNotFoundError:
        return _region_not_found(region)
    return [to_marker_response(store) for store in stores]


@router.get("/summary", response_model=ConvenienceRegionSummaryResponse)
def summarize_region(
    region: str,
    use_case: ConvenienceStoreQueryUseCase = Depends(get_convenience_store_query_use_case),
) -> ConvenienceRegionSummaryResponse | JSONResponse:
    try:
        return to_summary_response(use_case.summarize_region(region))
    except RegionNotFoundError:
        return _region_not_found(region)
