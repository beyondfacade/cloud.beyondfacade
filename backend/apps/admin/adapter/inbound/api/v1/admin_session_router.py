from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse

from apps.admin.adapter.inbound.api.client_ip import client_ip_from_scope
from apps.admin.adapter.inbound.api.oauth_cookie import (
    OAuthHandshake,
    clear_oauth_cookie,
    read_oauth_cookie,
    safe_next,
    set_oauth_cookie,
)
from apps.admin.adapter.inbound.api.schemas.admin_session_schema import (
    AdminMeResponse,
    AuthProvidersResponse,
    LoginRequest,
    PasswordChangeRequest,
    SignupRequest,
    UsernameChangeRequest,
)
from apps.admin.adapter.inbound.api.session_cookie import (
    SESSION_COOKIE,
    clear_session_cookie,
    set_session_cookie,
)
from apps.admin.adapter.inbound.mappers.admin_session_mapper import to_me_response
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.errors import AdminError
from apps.admin.app.ports.input.admin_session_use_case import AdminSessionUseCase
from apps.admin.dependencies.admin_dependencies import get_admin_session_use_case
from apps.admin.dependencies.admin_guard import require_admin

router = APIRouter(prefix="/admin/auth", tags=["admin"])

# 구글 왕복은 브라우저 이동이라 JSON 오류 대신 로그인 화면으로 돌려보내며 이유 코드를 붙인다
_LOGIN_PAGE = "/login"


def _login_error(error: AdminError) -> RedirectResponse:
    response = RedirectResponse(f"{_LOGIN_PAGE}?error={error.code}", status_code=302)
    clear_oauth_cookie(response)
    return response


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


@router.post("/signup", response_model=AdminMeResponse, status_code=201)
def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    use_case: AdminSessionUseCase = Depends(get_admin_session_use_case),
) -> AdminMeResponse:
    result = use_case.signup(body.username, body.email, body.password, client_ip_from_scope(request.scope))
    set_session_cookie(response, result.token, result.expires_at)
    return to_me_response(result.principal)


@router.get("/providers", response_model=AuthProvidersResponse)
def providers(use_case: AdminSessionUseCase = Depends(get_admin_session_use_case)) -> AuthProvidersResponse:
    return AuthProvidersResponse(google=use_case.google_enabled())


@router.get("/google/start")
def google_start(
    next_path: str | None = Query(None, alias="next", max_length=512),
    use_case: AdminSessionUseCase = Depends(get_admin_session_use_case),
) -> RedirectResponse:
    try:
        start = use_case.begin_google_login()
    except AdminError as error:
        return _login_error(error)
    response = RedirectResponse(start.url, status_code=302)
    set_oauth_cookie(response, OAuthHandshake(start.state, start.code_verifier, safe_next(next_path)))
    return response


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str = "",
    state: str = "",
    use_case: AdminSessionUseCase = Depends(get_admin_session_use_case),
) -> RedirectResponse:
    handshake = read_oauth_cookie(request)
    try:
        result = use_case.finish_google_login(
            code,
            state,
            handshake.state if handshake else None,
            handshake.code_verifier if handshake else "",
            client_ip_from_scope(request.scope),
        )
    except AdminError as error:
        return _login_error(error)
    response = RedirectResponse(handshake.next_path, status_code=302)
    clear_oauth_cookie(response)
    set_session_cookie(response, result.token, result.expires_at)
    return response


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


@router.patch("/username", response_model=AdminMeResponse)
def change_username(
    body: UsernameChangeRequest,
    request: Request,
    principal: AdminPrincipalDto = Depends(require_admin),
    use_case: AdminSessionUseCase = Depends(get_admin_session_use_case),
) -> AdminMeResponse:
    return to_me_response(use_case.change_username(principal, body.username, client_ip_from_scope(request.scope)))
