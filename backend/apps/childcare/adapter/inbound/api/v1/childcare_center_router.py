from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.childcare.adapter.inbound.api.schemas.childcare_center_schema import (
    ChildcareCenterMarkerResponse,
)
from apps.childcare.adapter.inbound.mappers.childcare_center_mapper import to_marker_response
from apps.childcare.app.ports.input.childcare_center_use_case import ChildcareCenterQueryUseCase
from apps.childcare.dependencies.childcare_dependencies import (
    get_childcare_center_query_use_case,
    region_not_found,
)
from apps.childcare.domain.errors import RegionNotFoundError

router = APIRouter(prefix="/childcare-centers", tags=["childcare"])


@router.get("/myself", response_model=ChildcareCenterMarkerResponse)
def myself(
    use_case: ChildcareCenterQueryUseCase = Depends(get_childcare_center_query_use_case),
) -> ChildcareCenterMarkerResponse:
    return to_marker_response(use_case.myself())


@router.get("", response_model=list[ChildcareCenterMarkerResponse])
def list_centers(
    region: str,
    use_case: ChildcareCenterQueryUseCase = Depends(get_childcare_center_query_use_case),
) -> list[ChildcareCenterMarkerResponse] | JSONResponse:
    try:
        centers = use_case.list_centers(region)
    except RegionNotFoundError:
        return region_not_found(region)
    return [to_marker_response(center) for center in centers]
