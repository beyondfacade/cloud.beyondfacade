from datetime import datetime

from sqlalchemy import delete, func, select

from apps.admin.adapter.outbound.orm_mappers.admin_session_orm_mapper import to_entity, to_orm
from apps.admin.adapter.outbound.orms.admin_session_orm import AdminSessionOrm
from apps.admin.app.ports.output.admin_session_port import AdminSessionRepositoryPort
from apps.admin.domain.entities.admin_session_entity import AdminSession
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyAdminSessionRepository(AdminSessionRepositoryPort):
    def add(self, session_entity: AdminSession) -> None:
        with session_scope() as session:
            session.add(to_orm(session_entity))

    def get(self, token_hash: str) -> AdminSession | None:
        with session_scope() as session:
            orm = session.get(AdminSessionOrm, token_hash)
            return to_entity(orm) if orm else None

    def delete(self, token_hash: str) -> None:
        with session_scope() as session:
            session.execute(delete(AdminSessionOrm).where(AdminSessionOrm.token_hash == token_hash))

    def list_active_for_user(self, user_id: int, now: datetime) -> list[AdminSession]:
        with session_scope() as session:
            rows = session.execute(
                select(AdminSessionOrm)
                .where(AdminSessionOrm.admin_user_id == user_id, AdminSessionOrm.expires_at > now)
                .order_by(AdminSessionOrm.created_at.desc())
            ).scalars()
            return [to_entity(orm) for orm in rows]

    def delete_for_user(self, user_id: int, keep_token_hash: str | None = None) -> int:
        query = delete(AdminSessionOrm).where(AdminSessionOrm.admin_user_id == user_id)
        if keep_token_hash is not None:
            query = query.where(AdminSessionOrm.token_hash != keep_token_hash)
        with session_scope() as session:
            return session.execute(query).rowcount

    def count_active_by_user(self, now: datetime) -> dict[int, int]:
        with session_scope() as session:
            rows = session.execute(
                select(AdminSessionOrm.admin_user_id, func.count())
                .where(AdminSessionOrm.expires_at > now)
                .group_by(AdminSessionOrm.admin_user_id)
            ).all()
            return {user_id: count for user_id, count in rows}

    def delete_expired(self, now: datetime) -> int:
        with session_scope() as session:
            return session.execute(delete(AdminSessionOrm).where(AdminSessionOrm.expires_at <= now)).rowcount
