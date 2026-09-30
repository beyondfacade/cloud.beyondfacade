from fastapi import APIRouter, Depends, Request, Response

from apps.admin.adapter.inbound.api.client_ip import client_ip_from_scope
from apps.admin.adapter.inbound.api.schemas.admin_session_schema import (
    AdminMeResponse,
    LoginRequest,
    PasswordChangeRequest,
)
from apps.admin.adapter.inbound.api.session_cookie import (
    SESSION_COOKIE,
    clear_session_cookie,
    set_session_cookie,
)
from apps.admin.adapter.inbound.mappers.admin_session_mapper import to_me_response
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.ports.input.admin_session_use_case import AdminSessionUseCase
from apps.admin.dependencies.admin_dependencies import get_admin_session_use_case
from apps.admin.dependencies.admin_guard import require_admin

router = APIRouter(prefix="/admin/auth", tags=["admin"])


@router.get("/myself", response_model=AdminMeResponse)
def myself(use_case: AdminSessionUseCase = Depends(get_admin_session_use_case)) -> AdminMeResponse:
    return to_me_response(use_case.myself())


@router.post("/login", response_model=AdminMeResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    use_case: AdminSessionUseCase = Depends(get_admin_session_use_case),
) -> AdminMeResponse:
    result = use_case.login(body.username, body.password, client_ip_from_scope(request.scope))
    set_session_cookie(response, result.token, result.expires_at)
    return to_me_response(result.principal)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    use_case: AdminSessionUseCase = Depends(get_admin_session_use_case),
) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        use_case.logout(token)
    clear_session_cookie(response)


@router.get("/me", response_model=AdminMeResponse)
def me(principal: AdminPrincipalDto = Depends(require_admin)) -> AdminMeResponse:
    return to_me_response(principal)


@router.post("/password", status_code=204)
def change_password(
    body: PasswordChangeRequest,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: AdminSessionUseCase = Depends(get_admin_session_use_case),
) -> None:
    use_case.change_password(
        principal,
        request.cookies.get(SESSION_COOKIE, ""),
        body.current_password,
        body.new_password,
        client_ip_from_scope(request.scope),
    )
