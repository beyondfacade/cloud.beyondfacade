from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.store.adapter.inbound.api.schemas.store_schema import (
    StoreMarkerResponse,
    StoreResponse,
)
from apps.store.adapter.inbound.mappers.store_mapper import (
    to_marker_response,
    to_response,
)
from apps.store.app.ports.input.store_use_case import StoreUseCase
from apps.store.dependencies.store_dependencies import get_store_use_case
from apps.store.domain.errors import IndustryNotFoundError

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/myself", response_model=StoreResponse)
def myself(
    use_case: StoreUseCase = Depends(get_store_use_case),
) -> StoreResponse:
    return to_response(use_case.myself())


@router.get("", response_model=list[StoreMarkerResponse])
def list_open_stores(
    region: str,
    industry: str,
    use_case: StoreUseCase = Depends(get_store_use_case),
) -> list[StoreMarkerResponse] | JSONResponse:
    try:
        stores = use_case.list_open_stores(region, industry)
    except IndustryNotFoundError:
        # 에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "INDUSTRY_NOT_FOUND",
                    "message": f"지원하지 않는 industry: {industry}",
                }
            },
        )
    return [to_marker_response(store) for store in stores]
