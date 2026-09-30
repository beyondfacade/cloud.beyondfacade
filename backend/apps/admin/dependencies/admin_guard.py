"""관리자 권한 가드 (AOP Before) — 라우터는 Depends(require_admin | require_operator)로만 선언한다."""

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
        raise Unauthenticated("관리자 로그인이 필요합니다.")
    return principal


def require_operator(principal: AdminPrincipalDto = Depends(require_admin)) -> AdminPrincipalDto:
    if not principal.can_operate:
        raise ForbiddenRole("운영 관리자 권한이 필요합니다.")
    return principal
