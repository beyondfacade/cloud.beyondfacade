from fastapi import APIRouter, Depends

from apps.admin.adapter.inbound.api.schemas.access_event_schema import SecurityOverviewResponse
from apps.admin.adapter.inbound.mappers.access_event_mapper import to_overview_response
from apps.admin.app.ports.input.access_event_use_case import AccessEventUseCase
from apps.admin.dependencies.admin_dependencies import get_access_event_use_case
from apps.admin.dependencies.admin_guard import require_admin

router = APIRouter(prefix="/admin/security", tags=["admin"])


@router.get("/myself", response_model=SecurityOverviewResponse)
def myself(use_case: AccessEventUseCase = Depends(get_access_event_use_case)) -> SecurityOverviewResponse:
    return to_overview_response(use_case.myself())


@router.get("/overview", response_model=SecurityOverviewResponse, dependencies=[Depends(require_admin)])
def overview(use_case: AccessEventUseCase = Depends(get_access_event_use_case)) -> SecurityOverviewResponse:
    return to_overview_response(use_case.overview())
