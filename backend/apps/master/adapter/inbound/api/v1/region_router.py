from fastapi import APIRouter, Depends

from apps.master.adapter.inbound.api.schemas.region_schema import RegionResponse
from apps.master.adapter.inbound.mappers.region_mapper import to_response
from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.dependencies.region_dependencies import get_region_use_case

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
