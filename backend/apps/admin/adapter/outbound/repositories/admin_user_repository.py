from datetime import datetime

from sqlalchemy import select, update

from apps.admin.adapter.outbound.orm_mappers.admin_user_orm_mapper import apply_to_orm, to_entity
from apps.admin.adapter.outbound.orms.admin_user_orm import AdminUserOrm
from apps.admin.app.ports.output.admin_user_port import AdminUserRepositoryPort
from apps.admin.domain.entities.admin_user_entity import AdminUser
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyAdminUserRepository(AdminUserRepositoryPort):
    def get_by_username(self, username: str) -> AdminUser | None:
        with session_scope() as session:
            orm = session.execute(select(AdminUserOrm).where(AdminUserOrm.username == username)).scalar_one_or_none()
            return to_entity(orm) if orm else None

    def get_by_id(self, user_id: int) -> AdminUser | None:
        with session_scope() as session:
            orm = session.get(AdminUserOrm, user_id)
            return to_entity(orm) if orm else None

    def save(self, user: AdminUser) -> AdminUser:
        with session_scope() as session:
            orm = session.execute(
                select(AdminUserOrm).where(AdminUserOrm.username == user.username)
            ).scalar_one_or_none()
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
