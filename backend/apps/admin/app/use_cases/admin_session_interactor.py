import secrets
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from functools import cache

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto, GoogleLoginStartDto, LoginResultDto
from apps.admin.app.dtos.google_identity_dto import GoogleIdentityDto
from apps.admin.app.errors import (
    EmailTaken,
    GoogleEmailUnverified,
    GoogleLoginFailed,
    GoogleNotConfigured,
    InvalidCredentials,
    InvalidEmail,
    InvalidUsername,
    LoginThrottled,
    OAuthStateMismatch,
    Unauthenticated,
    UsernameTaken,
    WeakPassword,
    WrongPassword,
)
from apps.admin.app.ports.input.admin_session_use_case import AdminSessionUseCase
from apps.admin.app.ports.output.access_event_port import AccessEventRepositoryPort
from apps.admin.app.ports.output.admin_audit_port import AdminAuditRepositoryPort
from apps.admin.app.ports.output.admin_session_port import AdminSessionRepositoryPort
from apps.admin.app.ports.output.admin_user_port import AdminUserRepositoryPort
from apps.admin.app.ports.output.google_identity_port import GoogleIdentityPort
from apps.admin.app.use_cases.audit_trail import audit_entry
from apps.admin.domain.entities.access_event_entity import AccessEvent, AccessEventKind
from apps.admin.domain.entities.admin_audit_entity import AuditAction
from apps.admin.domain.entities.admin_session_entity import AdminSession
from apps.admin.domain.entities.admin_user_entity import AdminRole, AdminUser
from apps.admin.domain.services.account_policy import (
    email_problem,
    normalize_email,
    password_problem,
    username_candidates,
    username_problem,
)
from apps.admin.domain.services.login_policy import SIGNUP_LIMIT, SIGNUP_WINDOW, THROTTLE_LIMIT, THROTTLE_WINDOW
from apps.admin.domain.services.oauth_handshake import new_oauth_state, new_pkce_pair
from apps.admin.domain.services.password_hasher import hash_password, verify_password
from apps.admin.domain.services.session_token import SESSION_TTL, hash_token, new_session_token

_LOGIN_PATH = "/admin/auth/login"
_SIGNUP_PATH = "/admin/auth/signup"
_GOOGLE_PATH = "/admin/auth/google/callback"


@cache
def _dummy_hash() -> str:
    """없는 계정도 scrypt를 한 번 돌려 응답 시간으로 계정 존재를 알 수 없게 한다."""
    return hash_password("metabole-timing-equalizer")


def to_principal(user: AdminUser) -> AdminPrincipalDto:
    return AdminPrincipalDto(id=user.id, username=user.username, role=user.role.value, can_operate=user.role.can_operate)


class AdminSessionInteractor(AdminSessionUseCase):
    def __init__(
        self,
        users: AdminUserRepositoryPort,
        sessions: AdminSessionRepositoryPort,
        events: AccessEventRepositoryPort,
        audit: AdminAuditRepositoryPort,
        google: GoogleIdentityPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._events = events
        self._audit = audit
        self._google = google
        self._clock = clock

    def myself(self) -> AdminPrincipalDto:
        return AdminPrincipalDto(id=0, username="myself", role="viewer", can_operate=False)

    def login(self, login_id: str, password: str, ip: str | None) -> LoginResultDto:
        now = self._clock()
        if self._events.count(AccessEventKind.LOGIN_FAILED, ip, now - THROTTLE_WINDOW) >= THROTTLE_LIMIT:
            self._record(AccessEventKind.LOGIN_THROTTLED, ip, 429, login_id, None, now)
            raise LoginThrottled("로그인 실패가 너무 많습니다. 10분 뒤에 다시 시도하세요.")

        user = self._find_for_login(login_id)
        stored = user.password_hash if user else None
        password_ok = verify_password(password, stored or _dummy_hash())
        if user is None or stored is None or not user.is_active or not password_ok:
            self._record(AccessEventKind.LOGIN_FAILED, ip, 401, login_id, None, now)
            raise InvalidCredentials("아이디 또는 비밀번호가 올바르지 않습니다.")

        self._record(AccessEventKind.LOGIN_SUCCEEDED, ip, 200, user.username, user.id, now)
        return self._issue(user, ip, now)

    def signup(self, username: str, email: str, password: str, ip: str | None) -> LoginResultDto:
        now = self._clock()
        if self._events.count(AccessEventKind.SIGNUP, ip, now - SIGNUP_WINDOW) >= SIGNUP_LIMIT:
            self._record(AccessEventKind.LOGIN_THROTTLED, ip, 429, username, None, now, _SIGNUP_PATH)
            raise LoginThrottled("가입이 너무 많습니다. 한 시간 뒤에 다시 시도하세요.")

        email = normalize_email(email)
        if problem := username_problem(username):
            raise InvalidUsername(problem)
        if problem := email_problem(email):
            raise InvalidEmail(problem)
        if problem := password_problem(password):
            raise WeakPassword(problem)
        if self._users.get_by_username(username) is not None:
            raise UsernameTaken(f"이미 있는 계정명입니다: {username}")
        if self._users.get_by_email(email) is not None:
            raise EmailTaken("이미 가입된 이메일입니다.")

        user = self._users.save(
            AdminUser(username=username, password_hash=hash_password(password), role=AdminRole.VIEWER, email=email)
        )
        self._record(AccessEventKind.SIGNUP, ip, 201, username, user.id, now, _SIGNUP_PATH)
        return self._issue(user, ip, now)

    def google_enabled(self) -> bool:
        return self._google.is_configured()

    def begin_google_login(self) -> GoogleLoginStartDto:
        if not self._google.is_configured():
            raise GoogleNotConfigured("구글 로그인이 아직 설정되지 않았습니다.")
        state = new_oauth_state()
        verifier, challenge = new_pkce_pair()
        return GoogleLoginStartDto(url=self._google.authorization_url(state, challenge), state=state, code_verifier=verifier)

    def finish_google_login(
        self, code: str, state: str, expected_state: str | None, code_verifier: str, ip: str | None
    ) -> LoginResultDto:
        if not state or not expected_state or not secrets.compare_digest(state.encode(), expected_state.encode()):
            raise OAuthStateMismatch("로그인 요청이 만료되었거나 올바르지 않습니다. 다시 시도하세요.")
        identity = self._google.exchange(code, code_verifier) if code else None
        if identity is None:
            raise GoogleLoginFailed("구글 로그인을 마치지 못했습니다.")
        if not identity.email_verified:
            raise GoogleEmailUnverified("구글에서 확인된 이메일이 아닙니다.")

        now = self._clock()
        user = self._users.get_by_google_sub(identity.sub) or self._google_signup(identity, ip, now)
        if not user.is_active:
            self._record(AccessEventKind.LOGIN_FAILED, ip, 401, user.username, user.id, now, _GOOGLE_PATH, "GET")
            raise InvalidCredentials("이용이 정지된 계정입니다.")
        self._record(AccessEventKind.LOGIN_SUCCEEDED, ip, 302, user.username, user.id, now, _GOOGLE_PATH, "GET")
        return self._issue(user, ip, now)

    def logout(self, token: str) -> None:
        self._sessions.delete(hash_token(token))

    def authenticate(self, token: str) -> AdminPrincipalDto | None:
        session = self._sessions.get(hash_token(token))
        if session is None or session.is_expired(self._clock()):
            return None
        user = self._users.get_by_id(session.admin_user_id)
        if user is None or not user.is_active:
            return None
        return to_principal(user)

    def change_password(
        self, principal: AdminPrincipalDto, token: str, current_password: str, new_password: str, ip: str | None
    ) -> None:
        user = self._users.get_by_id(principal.id)
        if user is None:
            raise Unauthenticated("로그인이 필요합니다.")
        if user.password_hash is None:
            raise WrongPassword("구글로 가입한 계정은 비밀번호가 없습니다. 관리자에게 비밀번호 설정을 요청하세요.")
        if not verify_password(current_password, user.password_hash):
            raise WrongPassword("현재 비밀번호가 올바르지 않습니다.")
        if problem := password_problem(new_password):
            raise WeakPassword(problem)
        self._users.save(replace(user, password_hash=hash_password(new_password)))
        self._sessions.delete_for_user(user.id, hash_token(token))
        self._audit.add(audit_entry(self._clock(), principal, AuditAction.PASSWORD_CHANGE, user.username, ip=ip))

    def _find_for_login(self, login_id: str) -> AdminUser | None:
        """계정명 규칙에는 @가 없어 이메일과 겹치지 않는다."""
        if "@" in login_id:
            return self._users.get_by_email(normalize_email(login_id))
        return self._users.get_by_username(login_id)

    def _google_signup(self, identity: GoogleIdentityDto, ip: str | None, now: datetime) -> AdminUser:
        email = normalize_email(identity.email)
        if self._users.get_by_email(email) is not None:
            raise EmailTaken("이 이메일로 가입된 계정이 있습니다. 아이디와 비밀번호로 로그인하세요.")
        username = next(name for name in username_candidates(email) if self._users.get_by_username(name) is None)
        user = self._users.save(
            AdminUser(
                username=username, password_hash=None, role=AdminRole.VIEWER, email=email, google_sub=identity.sub
            )
        )
        self._record(AccessEventKind.SIGNUP, ip, 302, username, user.id, now, _GOOGLE_PATH, "GET")
        return user

    def _issue(self, user: AdminUser, ip: str | None, now: datetime) -> LoginResultDto:
        raw, token_hash = new_session_token()
        expires_at = now + SESSION_TTL
        self._sessions.add(
            AdminSession(token_hash=token_hash, admin_user_id=user.id, created_at=now, expires_at=expires_at, ip=ip)
        )
        self._users.touch_login(user.id, now)
        return LoginResultDto(token=raw, expires_at=expires_at, principal=to_principal(user))

    def _record(
        self,
        kind: AccessEventKind,
        ip: str | None,
        status: int,
        username: str,
        user_id: int | None,
        now: datetime,
        path: str = _LOGIN_PATH,
        method: str = "POST",
    ) -> None:
        self._events.add(
            AccessEvent(
                occurred_at=now,
                kind=kind,
                ip=ip,
                method=method,
                path=path,
                status_code=status,
                username=username[:64],
                admin_user_id=user_id,
            )
        )
