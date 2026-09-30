from fastapi import APIRouter, Depends, Query

from apps.admin.adapter.inbound.api.schemas.admin_audit_schema import AuditPageResponse
from apps.admin.adapter.inbound.mappers.admin_audit_mapper import to_page_response
from apps.admin.app.ports.input.admin_audit_use_case import AdminAuditUseCase
from apps.admin.dependencies.admin_dependencies import get_admin_audit_use_case
from apps.admin.dependencies.admin_guard import require_admin
from apps.admin.domain.entities.admin_audit_entity import AuditAction

router = APIRouter(prefix="/admin/security/audit", tags=["admin"])


@router.get("/myself", response_model=AuditPageResponse)
def myself(use_case: AdminAuditUseCase = Depends(get_admin_audit_use_case)) -> AuditPageResponse:
    return to_page_response(use_case.myself())


@router.get("", response_model=AuditPageResponse, dependencies=[Depends(require_admin)])
def page(
    action: AuditAction | None = None,
    before_id: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=200),
    use_case: AdminAuditUseCase = Depends(get_admin_audit_use_case),
) -> AuditPageResponse:
    return to_page_response(use_case.page(action, before_id, limit))
