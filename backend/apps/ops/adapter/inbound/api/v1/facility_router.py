from fastapi import APIRouter, Depends

from apps.admin.dependencies.admin_guard import require_admin
from apps.ops.adapter.inbound.api.schemas.facility_schema import FacilitySnapshotResponse, ServiceCheckResponse
from apps.ops.adapter.inbound.mappers.facility_mapper import to_service_response, to_snapshot_response
from apps.ops.app.ports.input.facility_use_case import FacilityUseCase
from apps.ops.dependencies.ops_dependencies import get_facility_use_case

router = APIRouter(prefix="/admin/facility", tags=["admin"])


@router.get("/myself", response_model=ServiceCheckResponse)
def myself(use_case: FacilityUseCase = Depends(get_facility_use_case)) -> ServiceCheckResponse:
    return to_service_response(use_case.myself())


@router.get("/snapshot", response_model=FacilitySnapshotResponse, dependencies=[Depends(require_admin)])
def snapshot(use_case: FacilityUseCase = Depends(get_facility_use_case)) -> FacilitySnapshotResponse:
    return to_snapshot_response(use_case.snapshot())
