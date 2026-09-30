from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from functools import cache

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto, LoginResultDto
from apps.admin.app.errors import InvalidCredentials, LoginThrottled, Unauthenticated, WeakPassword, WrongPassword
from apps.admin.app.ports.input.admin_session_use_case import AdminSessionUseCase
from apps.admin.app.ports.output.access_event_port import AccessEventRepositoryPort
from apps.admin.app.ports.output.admin_audit_port import AdminAuditRepositoryPort
from apps.admin.app.ports.output.admin_session_port import AdminSessionRepositoryPort
from apps.admin.app.ports.output.admin_user_port import AdminUserRepositoryPort
from apps.admin.app.use_cases.audit_trail import audit_entry
from apps.admin.domain.entities.access_event_entity import AccessEvent, AccessEventKind
from apps.admin.domain.entities.admin_audit_entity import AuditAction
from apps.admin.domain.entities.admin_session_entity import AdminSession
from apps.admin.domain.entities.admin_user_entity import AdminUser
from apps.admin.domain.services.account_policy import password_problem
from apps.admin.domain.services.login_policy import THROTTLE_LIMIT, THROTTLE_WINDOW
from apps.admin.domain.services.password_hasher import hash_password, verify_password
from apps.admin.domain.services.session_token import SESSION_TTL, hash_token, new_session_token

_LOGIN_PATH = "/admin/auth/login"


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
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._events = events
        self._audit = audit
        self._clock = clock

    def myself(self) -> AdminPrincipalDto:
        return AdminPrincipalDto(id=0, username="myself", role="viewer", can_operate=False)

    def login(self, username: str, password: str, ip: str | None) -> LoginResultDto:
        now = self._clock()
        if self._events.count(AccessEventKind.LOGIN_FAILED, ip, now - THROTTLE_WINDOW) >= THROTTLE_LIMIT:
            self._record(AccessEventKind.LOGIN_THROTTLED, ip, 429, username, None, now)
            raise LoginThrottled("로그인 실패가 너무 많습니다. 10분 뒤에 다시 시도하세요.")

        user = self._users.get_by_username(username)
        password_ok = verify_password(password, user.password_hash if user else _dummy_hash())
        if user is None or not user.is_active or not password_ok:
            self._record(AccessEventKind.LOGIN_FAILED, ip, 401, username, None, now)
            raise InvalidCredentials("아이디 또는 비밀번호가 올바르지 않습니다.")

        raw, token_hash = new_session_token()
        expires_at = now + SESSION_TTL
        self._sessions.add(
            AdminSession(token_hash=token_hash, admin_user_id=user.id, created_at=now, expires_at=expires_at, ip=ip)
        )
        self._users.touch_login(user.id, now)
        self._record(AccessEventKind.LOGIN_SUCCEEDED, ip, 200, username, user.id, now)
        return LoginResultDto(token=raw, expires_at=expires_at, principal=to_principal(user))

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
            raise Unauthenticated("관리자 로그인이 필요합니다.")
        if not verify_password(current_password, user.password_hash):
            raise WrongPassword("현재 비밀번호가 올바르지 않습니다.")
        if problem := password_problem(new_password):
            raise WeakPassword(problem)
        self._users.save(replace(user, password_hash=hash_password(new_password)))
        self._sessions.delete_for_user(user.id, hash_token(token))
        self._audit.add(audit_entry(self._clock(), principal, AuditAction.PASSWORD_CHANGE, user.username, ip=ip))

    def _record(
        self, kind: AccessEventKind, ip: str | None, status: int, username: str, user_id: int | None, now: datetime
    ) -> None:
        self._events.add(
            AccessEvent(
                occurred_at=now,
                kind=kind,
                ip=ip,
                method="POST",
                path=_LOGIN_PATH,
                status_code=status,
                username=username[:64],
                admin_user_id=user_id,
            )
        )
