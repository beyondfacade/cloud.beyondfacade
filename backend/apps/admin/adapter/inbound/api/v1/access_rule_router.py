from fastapi import APIRouter, Depends, Request

from apps.admin.adapter.inbound.api.client_ip import client_ip_from_scope
from apps.admin.adapter.inbound.api.device_cookie import client_from_scope
from apps.admin.adapter.inbound.api.schemas.access_rule_schema import (
    AccessRuleCreateRequest,
    AccessRuleResponse,
    CurrentDeviceResponse,
)
from apps.admin.adapter.inbound.mappers.access_rule_mapper import to_device_response, to_response
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.ports.input.access_rule_use_case import AccessRuleUseCase
from apps.admin.dependencies.admin_dependencies import get_access_rule_use_case
from apps.admin.dependencies.admin_guard import require_admin, require_operator

router = APIRouter(prefix="/admin/security/access-rules", tags=["admin"])


@router.get("/myself", response_model=AccessRuleResponse)
def myself(use_case: AccessRuleUseCase = Depends(get_access_rule_use_case)) -> AccessRuleResponse:
    return to_response(use_case.myself())


@router.get("", response_model=list[AccessRuleResponse], dependencies=[Depends(require_admin)])
def list_active(use_case: AccessRuleUseCase = Depends(get_access_rule_use_case)) -> list[AccessRuleResponse]:
    return [to_response(dto) for dto in use_case.list_active()]


@router.get("/current-device", response_model=CurrentDeviceResponse, dependencies=[Depends(require_admin)])
def current_device(
    request: Request, use_case: AccessRuleUseCase = Depends(get_access_rule_use_case)
) -> CurrentDeviceResponse:
    return to_device_response(use_case.current_device(client_from_scope(request.scope)))


@router.post("", response_model=AccessRuleResponse, status_code=201)
def create(
    body: AccessRuleCreateRequest,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_operator),
    use_case: AccessRuleUseCase = Depends(get_access_rule_use_case),
) -> AccessRuleResponse:
    dto = use_case.create(
        body.policy, body.target, body.value, body.note, body.ttl_minutes, principal, client_from_scope(request.scope)
    )
    return to_response(dto)


@router.delete("/{rule_id}", status_code=204)
def delete(
    rule_id: int,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_operator),
    use_case: AccessRuleUseCase = Depends(get_access_rule_use_case),
) -> None:
    use_case.delete(rule_id, principal, client_ip_from_scope(request.scope))
