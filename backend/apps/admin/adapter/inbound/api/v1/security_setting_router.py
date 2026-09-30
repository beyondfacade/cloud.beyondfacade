from fastapi import APIRouter, Depends, Request

from apps.admin.adapter.inbound.api.client_ip import client_ip_from_scope
from apps.admin.adapter.inbound.api.schemas.security_setting_schema import AutoDefenseResponse, AutoDefenseUpdateRequest
from apps.admin.adapter.inbound.mappers.security_setting_mapper import to_response
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.ports.input.security_setting_use_case import SecuritySettingUseCase
from apps.admin.dependencies.admin_dependencies import get_security_setting_use_case
from apps.admin.dependencies.admin_guard import require_admin, require_operator

router = APIRouter(prefix="/admin/security/settings", tags=["admin"])


@router.get("/myself", response_model=AutoDefenseResponse)
def myself(use_case: SecuritySettingUseCase = Depends(get_security_setting_use_case)) -> AutoDefenseResponse:
    return to_response(use_case.myself())


@router.get("/auto-defense", response_model=AutoDefenseResponse, dependencies=[Depends(require_admin)])
def auto_defense(use_case: SecuritySettingUseCase = Depends(get_security_setting_use_case)) -> AutoDefenseResponse:
    return to_response(use_case.auto_defense())


@router.put("/auto-defense", response_model=AutoDefenseResponse)
def set_auto_defense(
    body: AutoDefenseUpdateRequest,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_operator),
    use_case: SecuritySettingUseCase = Depends(get_security_setting_use_case),
) -> AutoDefenseResponse:
    return to_response(use_case.set_auto_defense(body.enabled, principal, client_ip_from_scope(request.scope)))
