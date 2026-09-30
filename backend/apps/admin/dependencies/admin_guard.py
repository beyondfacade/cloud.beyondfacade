"""등급 가드 (AOP Before) — 읽기는 Depends(require_admin: 로그인한 일반 이상), 쓰기는 Depends(require_operator: 관리자)."""

from fastapi import Depends, Request

from apps.admin.adapter.inbound.api.session_cookie import SESSION_COOKIE
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.errors import ForbiddenRole, Unauthenticated
from apps.admin.app.ports.input.admin_session_use_case import AdminSessionUseCase
from apps.admin.dependencies.admin_dependencies import get_admin_session_use_case


def require_admin(
    request: Request,
    use_case: AdminSessionUseCase = Depends(get_admin_session_use_case),
) -> AdminPrincipalDto:
    token = request.cookies.get(SESSION_COOKIE)
    principal = use_case.authenticate(token) if token else None
    if principal is None:
        raise Unauthenticated("로그인이 필요합니다.")
    return principal


def require_operator(principal: AdminPrincipalDto = Depends(require_admin)) -> AdminPrincipalDto:
    if not principal.can_operate:
        raise ForbiddenRole("관리자 권한이 필요합니다.")
    return principal
