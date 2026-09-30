from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.ports.input.admin_user_use_case import AdminUserUseCase
from apps.admin.app.ports.output.admin_user_port import AdminUserRepositoryPort
from apps.admin.app.use_cases.admin_session_interactor import to_principal
from apps.admin.domain.entities.admin_user_entity import AdminRole, AdminUser
from apps.admin.domain.services.password_hasher import hash_password

_MIN_PASSWORD_LENGTH = 12


class AdminUserInteractor(AdminUserUseCase):
    def __init__(self, users: AdminUserRepositoryPort) -> None:
        self._users = users

    def upsert(self, username: str, password: str, role: str) -> AdminPrincipalDto:
        if len(password) < _MIN_PASSWORD_LENGTH:
            raise ValueError(f"비밀번호는 {_MIN_PASSWORD_LENGTH}자 이상이어야 합니다.")
        user = AdminUser(username=username, password_hash=hash_password(password), role=AdminRole(role))
        return to_principal(self._users.save(user))
