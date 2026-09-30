from sqlalchemy import delete

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
