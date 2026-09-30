from datetime import datetime

from sqlalchemy import delete, select

from apps.admin.adapter.outbound.orm_mappers.admin_audit_orm_mapper import to_entity, to_orm
from apps.admin.adapter.outbound.orms.admin_audit_orm import AdminAuditOrm
from apps.admin.app.ports.output.admin_audit_port import AdminAuditRepositoryPort
from apps.admin.domain.entities.admin_audit_entity import AdminAudit, AuditAction
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyAdminAuditRepository(AdminAuditRepositoryPort):
    def add(self, entry: AdminAudit) -> None:
        with session_scope() as session:
            session.add(to_orm(entry))

    def page(self, action: AuditAction | None, before_id: int | None, limit: int) -> list[AdminAudit]:
        query = select(AdminAuditOrm).order_by(AdminAuditOrm.id.desc()).limit(limit)
        if action is not None:
            query = query.where(AdminAuditOrm.action == action.value)
        if before_id is not None:
            query = query.where(AdminAuditOrm.id < before_id)
        with session_scope() as session:
            return [to_entity(orm) for orm in session.execute(query).scalars()]

    def delete_before(self, cutoff: datetime) -> int:
        with session_scope() as session:
            return session.execute(delete(AdminAuditOrm).where(AdminAuditOrm.occurred_at < cutoff)).rowcount
