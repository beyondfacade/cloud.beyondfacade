from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.childcare.adapter.inbound.api.schemas.childcare_center_stat_schema import (
    ChildcareRegionSummaryResponse,
)
from apps.childcare.adapter.inbound.mappers.childcare_center_stat_mapper import (
    to_summary_response,
)
from apps.childcare.app.ports.input.childcare_center_stat_use_case import (
    ChildcareCenterStatUseCase,
)
from apps.childcare.dependencies.childcare_dependencies import (
    get_childcare_center_stat_use_case,
    region_not_found,
)
from apps.childcare.domain.errors import RegionNotFoundError

router = APIRouter(prefix="/childcare-center-stats", tags=["childcare"])


@router.get("/myself", response_model=ChildcareRegionSummaryResponse)
def myself(
    use_case: ChildcareCenterStatUseCase = Depends(get_childcare_center_stat_use_case),
) -> ChildcareRegionSummaryResponse:
    return to_summary_response(use_case.myself())


@router.get("/summary", response_model=ChildcareRegionSummaryResponse)
def summarize_region(
    region: str,
    use_case: ChildcareCenterStatUseCase = Depends(get_childcare_center_stat_use_case),
) -> ChildcareRegionSummaryResponse | JSONResponse:
    try:
        return to_summary_response(use_case.summarize_region(region))
    except RegionNotFoundError:
        return region_not_found(region)
