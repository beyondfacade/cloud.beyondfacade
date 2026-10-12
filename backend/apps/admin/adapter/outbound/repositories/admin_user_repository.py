from datetime import datetime

from sqlalchemy import select, update

from apps.admin.adapter.outbound.orm_mappers.admin_user_orm_mapper import apply_to_orm, to_entity
from apps.admin.adapter.outbound.orms.admin_user_orm import AdminUserAvatarOrm, AdminUserOrm
from apps.admin.app.ports.output.admin_user_port import AdminUserRepositoryPort
from apps.admin.domain.entities.admin_user_entity import AdminUser
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyAdminUserRepository(AdminUserRepositoryPort):
    def get_by_username(self, username: str) -> AdminUser | None:
        with session_scope() as session:
            orm = session.execute(select(AdminUserOrm).where(AdminUserOrm.username == username)).scalar_one_or_none()
            return to_entity(orm) if orm else None

    def get_by_email(self, email: str) -> AdminUser | None:
        with session_scope() as session:
            orm = session.execute(select(AdminUserOrm).where(AdminUserOrm.email == email)).scalar_one_or_none()
            return to_entity(orm) if orm else None

    def get_by_google_sub(self, google_sub: str) -> AdminUser | None:
        with session_scope() as session:
            orm = session.execute(
                select(AdminUserOrm).where(AdminUserOrm.google_sub == google_sub)
            ).scalar_one_or_none()
            return to_entity(orm) if orm else None

    def get_by_id(self, user_id: int) -> AdminUser | None:
        with session_scope() as session:
            orm = session.get(AdminUserOrm, user_id)
            return to_entity(orm) if orm else None

    def save(self, user: AdminUser) -> AdminUser:
        with session_scope() as session:
            # 저장된 계정은 id로 찾아야 계정명을 바꿔도 같은 행을 고친다
            key = AdminUserOrm.id == user.id if user.id is not None else AdminUserOrm.username == user.username
            orm = session.execute(select(AdminUserOrm).where(key)).scalar_one_or_none()
            if orm is None:
                orm = AdminUserOrm()
                session.add(orm)
            apply_to_orm(user, orm)
            session.flush()
            session.refresh(orm)
            return to_entity(orm)

    def touch_login(self, user_id: int, at: datetime) -> None:
        with session_scope() as session:
            session.execute(update(AdminUserOrm).where(AdminUserOrm.id == user_id).values(last_login_at=at))

    def list_all(self) -> list[AdminUser]:
        with session_scope() as session:
            rows = session.execute(select(AdminUserOrm).order_by(AdminUserOrm.username)).scalars()
            return [to_entity(orm) for orm in rows]

    def save_avatar(self, user_id: int, media_type: str, content: bytes) -> int:
        with session_scope() as session:
            user = session.get(AdminUserOrm, user_id, with_for_update=True)
            avatar = session.get(AdminUserAvatarOrm, user_id)
            if avatar is None:
                avatar = AdminUserAvatarOrm(user_id=user_id)
                session.add(avatar)
            avatar.media_type = media_type
            avatar.content = content
            user.avatar_version = (user.avatar_version or 0) + 1
            return user.avatar_version

    def get_avatar(self, user_id: int) -> tuple[str, bytes] | None:
        with session_scope() as session:
            avatar = session.get(AdminUserAvatarOrm, user_id)
            return (avatar.media_type, avatar.content) if avatar else None
