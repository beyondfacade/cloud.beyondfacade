from fastapi import APIRouter, Depends, Query

from apps.admin.adapter.inbound.api.schemas.access_event_schema import (
    AccessEventPageResponse,
    SecurityOverviewResponse,
)
from apps.admin.adapter.inbound.mappers.access_event_mapper import to_event_page_response, to_overview_response
from apps.admin.app.ports.input.access_event_use_case import AccessEventUseCase
from apps.admin.dependencies.admin_dependencies import get_access_event_use_case
from apps.admin.dependencies.admin_guard import require_admin
from apps.admin.domain.entities.access_event_entity import AccessEventKind

router = APIRouter(prefix="/admin/security", tags=["admin"])


@router.get("/myself", response_model=SecurityOverviewResponse)
def myself(use_case: AccessEventUseCase = Depends(get_access_event_use_case)) -> SecurityOverviewResponse:
    return to_overview_response(use_case.myself())


@router.get("/overview", response_model=SecurityOverviewResponse, dependencies=[Depends(require_admin)])
def overview(use_case: AccessEventUseCase = Depends(get_access_event_use_case)) -> SecurityOverviewResponse:
    return to_overview_response(use_case.overview())


@router.get("/events", response_model=AccessEventPageResponse, dependencies=[Depends(require_admin)])
def events(
    kind: AccessEventKind | None = None,
    ip: str | None = Query(None, max_length=64),
    hours: int = Query(24, ge=1, le=24 * 90),
    before_id: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=200),
    use_case: AccessEventUseCase = Depends(get_access_event_use_case),
) -> AccessEventPageResponse:
    return to_event_page_response(use_case.events(kind, ip.strip() if ip else None, hours, before_id, limit))
