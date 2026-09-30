from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.dtos.admin_user_dto import AdminSessionInfoDto, AdminUserDto
from apps.admin.app.errors import (
    AdminUserNotFound,
    ForbiddenRole,
    InvalidUsername,
    LastOperator,
    SelfChange,
    UsernameTaken,
    WeakPassword,
)
from apps.admin.app.ports.input.admin_user_use_case import AdminUserUseCase
from apps.admin.app.ports.output.admin_audit_port import AdminAuditRepositoryPort
from apps.admin.app.ports.output.admin_session_port import AdminSessionRepositoryPort
from apps.admin.app.ports.output.admin_user_port import AdminUserRepositoryPort
from apps.admin.app.use_cases.admin_session_interactor import to_principal
from apps.admin.app.use_cases.audit_trail import audit_entry
from apps.admin.domain.entities.admin_audit_entity import AuditAction
from apps.admin.domain.entities.admin_user_entity import AdminRole, AdminUser
from apps.admin.domain.services.account_policy import leaves_no_active_operator, password_problem, username_problem
from apps.admin.domain.services.password_hasher import hash_password
from apps.admin.domain.services.session_token import hash_token

SESSION_PUBLIC_ID_LENGTH = 12

_STATUS_FILTERS: dict[str, Callable[[AdminUser], bool]] = {
    "all": lambda user: True,
    "active": lambda user: user.is_active,
    "suspended": lambda user: not user.is_active,
}
_ACTIVE_ACTION = {True: AuditAction.USER_REACTIVATE, False: AuditAction.USER_SUSPEND}


def _check_password(password: str) -> None:
    if problem := password_problem(password):
        raise WeakPassword(problem)


class AdminUserInteractor(AdminUserUseCase):
    def __init__(
        self,
        users: AdminUserRepositoryPort,
        sessions: AdminSessionRepositoryPort,
        audit: AdminAuditRepositoryPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._audit = audit
        self._clock = clock

    def myself(self) -> AdminUserDto:
        return AdminUserDto(
            username="myself", role="viewer", is_active=True, created_at=datetime(2026, 9, 30, tzinfo=UTC),
            last_login_at=None, active_sessions=0, email=None, has_password=True, has_google=False,
        )

    def upsert(self, username: str, password: str, role: str) -> AdminPrincipalDto:
        if problem := username_problem(username):
            raise InvalidUsername(problem)
        _check_password(password)
        fields = {"password_hash": hash_password(password), "role": AdminRole(role), "is_active": True}
        existing = self._users.get_by_username(username)
        user = replace(existing, **fields) if existing else AdminUser(username=username, **fields)
        return to_principal(self._users.save(user))

    def set_role(self, username: str, role: str) -> AdminPrincipalDto:
        return to_principal(self._users.save(replace(self._get(username), role=AdminRole(role))))

    def list_users(self, q: str, role: str | None, status: str) -> list[AdminUserDto]:
        needle = q.strip().lower()
        keep = _STATUS_FILTERS[status]
        wanted_role = AdminRole(role) if role else None
        sessions = self._sessions.count_active_by_user(self._clock())
        return [
            self._to_dto(user, sessions)
            for user in self._users.list_all()
            if (needle in user.username.lower() or needle in (user.email or ""))
            and keep(user)
            and (wanted_role is None or user.role is wanted_role)
        ]

    def create(
        self, actor: AdminPrincipalDto, username: str, role: str, password: str, ip: str | None
    ) -> AdminUserDto:
        if problem := username_problem(username):
            raise InvalidUsername(problem)
        _check_password(password)
        if self._users.get_by_username(username) is not None:
            raise UsernameTaken(f"이미 있는 계정명입니다: {username}")
        user = self._users.save(
            AdminUser(username=username, password_hash=hash_password(password), role=AdminRole(role))
        )
        self._record(actor, AuditAction.USER_CREATE, username, f"역할 {role}", ip)
        return self._to_dto(user, {})

    def change_role(self, actor: AdminPrincipalDto, username: str, role: str, ip: str | None) -> AdminUserDto:
        user = self._target(actor, username)
        new_role = AdminRole(role)
        if leaves_no_active_operator(self._users.list_all(), username, new_role, user.is_active):
            raise LastOperator("활성 관리자가 한 명은 남아 있어야 합니다.")
        saved = self._users.save(replace(user, role=new_role))
        self._record(actor, AuditAction.USER_ROLE, username, f"{user.role.value} → {new_role.value}", ip)
        return self._to_dto(saved, self._sessions.count_active_by_user(self._clock()))

    def set_active(self, actor: AdminPrincipalDto, username: str, active: bool, ip: str | None) -> AdminUserDto:
        user = self._target(actor, username)
        if leaves_no_active_operator(self._users.list_all(), username, user.role, active):
            raise LastOperator("활성 관리자가 한 명은 남아 있어야 합니다.")
        saved = self._users.save(replace(user, is_active=active))
        if not active:
            self._sessions.delete_for_user(user.id)
        self._record(actor, _ACTIVE_ACTION[active], username, "", ip)
        return self._to_dto(saved, self._sessions.count_active_by_user(self._clock()))

    def reset_password(self, actor: AdminPrincipalDto, username: str, password: str, ip: str | None) -> None:
        user = self._target(actor, username)
        _check_password(password)
        self._users.save(replace(user, password_hash=hash_password(password)))
        self._sessions.delete_for_user(user.id)
        self._record(actor, AuditAction.USER_PASSWORD_RESET, username, "", ip)

    def sessions(
        self, actor: AdminPrincipalDto, username: str, current_token: str | None
    ) -> list[AdminSessionInfoDto]:
        user = self._self_or_operator(actor, username)
        current_token_hash = hash_token(current_token) if current_token else None
        return [
            AdminSessionInfoDto(
                id=session.token_hash[:SESSION_PUBLIC_ID_LENGTH],
                created_at=session.created_at,
                expires_at=session.expires_at,
                ip=session.ip,
                current=session.token_hash == current_token_hash,
            )
            for session in self._sessions.list_active_for_user(user.id, self._clock())
        ]

    def revoke_sessions(
        self, actor: AdminPrincipalDto, username: str, current_token: str | None, ip: str | None
    ) -> int:
        user = self._self_or_operator(actor, username)
        keep = hash_token(current_token) if current_token and user.id == actor.id else None
        revoked = self._sessions.delete_for_user(user.id, keep)
        self._record(actor, AuditAction.USER_SESSIONS_REVOKE, username, f"{revoked}개", ip)
        return revoked

    def _get(self, username: str) -> AdminUser:
        user = self._users.get_by_username(username)
        if user is None:
            raise AdminUserNotFound(f"없는 계정입니다: {username}")
        return user

    def _target(self, actor: AdminPrincipalDto, username: str) -> AdminUser:
        """남의 계정을 바꾸는 조치 — 내 계정은 잠금 사고를 막으려 이 경로로 못 바꾼다."""
        user = self._get(username)
        if user.id == actor.id:
            raise SelfChange("내 계정의 등급·상태·비밀번호는 여기서 바꿀 수 없습니다.")
        return user

    def _self_or_operator(self, actor: AdminPrincipalDto, username: str) -> AdminUser:
        user = self._get(username)
        if user.id != actor.id and not actor.can_operate:
            raise ForbiddenRole("다른 계정의 세션은 관리자만 볼 수 있습니다.")
        return user

    def _record(self, actor: AdminPrincipalDto, action: AuditAction, target: str, detail: str, ip: str | None) -> None:
        self._audit.add(audit_entry(self._clock(), actor, action, target, detail, ip))

    @staticmethod
    def _to_dto(user: AdminUser, sessions: dict[int, int]) -> AdminUserDto:
        return AdminUserDto(
            username=user.username,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            active_sessions=sessions.get(user.id, 0),
            email=user.email,
            has_password=user.password_hash is not None,
            has_google=user.google_sub is not None,
        )
