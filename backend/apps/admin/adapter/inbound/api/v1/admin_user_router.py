"""인사팀 — 관리자 계정 목록·생성·역할·정지·비밀번호 재설정·세션."""

from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from apps.admin.adapter.inbound.api.client_ip import client_ip_from_scope
from apps.admin.adapter.inbound.api.schemas.admin_user_schema import (
    AdminPasswordResetRequest,
    AdminRoleRequest,
    AdminSessionListResponse,
    AdminStatusRequest,
    AdminUserCreateRequest,
    AdminUserListResponse,
    AdminUserResponse,
    RevokedSessionsResponse,
    RoleValue,
)
from apps.admin.adapter.inbound.api.session_cookie import SESSION_COOKIE
from apps.admin.adapter.inbound.mappers.admin_user_mapper import (
    to_session_list_response,
    to_user_list_response,
    to_user_response,
)
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.ports.input.admin_user_use_case import AdminUserUseCase
from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from apps.admin.dependencies.admin_guard import require_admin, require_operator

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.get("/myself", response_model=AdminUserResponse)
def myself(use_case: AdminUserUseCase = Depends(get_admin_user_use_case)) -> AdminUserResponse:
    return to_user_response(use_case.myself())


@router.get("", response_model=AdminUserListResponse, dependencies=[Depends(require_admin)])
def list_users(
    q: str = Query("", max_length=64),
    role: RoleValue | None = None,
    status: Literal["all", "active", "suspended"] = "all",
    use_case: AdminUserUseCase = Depends(get_admin_user_use_case),
) -> AdminUserListResponse:
    return to_user_list_response(use_case.list_users(q, role, status))


@router.post("", response_model=AdminUserResponse, status_code=201)
def create(
    body: AdminUserCreateRequest,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_operator),
    use_case: AdminUserUseCase = Depends(get_admin_user_use_case),
) -> AdminUserResponse:
    ip = client_ip_from_scope(request.scope)
    return to_user_response(use_case.create(principal, body.username, body.role, body.password, ip))


@router.patch("/{username}/role", response_model=AdminUserResponse)
def change_role(
    username: str,
    body: AdminRoleRequest,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_operator),
    use_case: AdminUserUseCase = Depends(get_admin_user_use_case),
) -> AdminUserResponse:
    return to_user_response(use_case.change_role(principal, username, body.role, client_ip_from_scope(request.scope)))


@router.patch("/{username}/status", response_model=AdminUserResponse)
def set_status(
    username: str,
    body: AdminStatusRequest,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_operator),
    use_case: AdminUserUseCase = Depends(get_admin_user_use_case),
) -> AdminUserResponse:
    return to_user_response(use_case.set_active(principal, username, body.active, client_ip_from_scope(request.scope)))


@router.put("/{username}/password", status_code=204)
def reset_password(
    username: str,
    body: AdminPasswordResetRequest,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_operator),
    use_case: AdminUserUseCase = Depends(get_admin_user_use_case),
) -> None:
    use_case.reset_password(principal, username, body.password, client_ip_from_scope(request.scope))


@router.get("/{username}/sessions", response_model=AdminSessionListResponse)
def sessions(
    username: str,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: AdminUserUseCase = Depends(get_admin_user_use_case),
) -> AdminSessionListResponse:
    return to_session_list_response(use_case.sessions(principal, username, request.cookies.get(SESSION_COOKIE)))


@router.delete("/{username}/sessions", response_model=RevokedSessionsResponse)
def revoke_sessions(
    username: str,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: AdminUserUseCase = Depends(get_admin_user_use_case),
) -> RevokedSessionsResponse:
    revoked = use_case.revoke_sessions(
        principal, username, request.cookies.get(SESSION_COOKIE), client_ip_from_scope(request.scope)
    )
    return RevokedSessionsResponse(revoked=revoked)
