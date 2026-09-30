from datetime import datetime

from sqlalchemy import delete, func, select

from apps.admin.adapter.outbound.orm_mappers.access_event_orm_mapper import to_entity, to_orm
from apps.admin.adapter.outbound.orms.access_event_orm import AccessEventOrm
from apps.admin.app.ports.output.access_event_port import AccessEventRepositoryPort
from apps.admin.domain.entities.access_event_entity import AccessEvent, AccessEventKind
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyAccessEventRepository(AccessEventRepositoryPort):
    def add(self, event: AccessEvent) -> None:
        with session_scope() as session:
            session.add(to_orm(event))

    def list_since(self, since: datetime, limit: int) -> list[AccessEvent]:
        with session_scope() as session:
            rows = session.execute(
                select(AccessEventOrm)
                .where(AccessEventOrm.occurred_at >= since)
                .order_by(AccessEventOrm.occurred_at.desc())
                .limit(limit)
            ).scalars()
            return [to_entity(orm) for orm in rows]

    def count(self, kind: AccessEventKind, ip: str | None, since: datetime) -> int:
        with session_scope() as session:
            return session.execute(
                select(func.count())
                .select_from(AccessEventOrm)
                .where(
                    AccessEventOrm.kind == kind.value,
                    AccessEventOrm.ip == ip,
                    AccessEventOrm.occurred_at >= since,
                )
            ).scalar_one()

    def search(
        self, kind: AccessEventKind | None, ip: str | None, since: datetime, before_id: int | None, limit: int
    ) -> list[AccessEvent]:
        query = (
            select(AccessEventOrm)
            .where(AccessEventOrm.occurred_at >= since)
            .order_by(AccessEventOrm.id.desc())
            .limit(limit)
        )
        if kind is not None:
            query = query.where(AccessEventOrm.kind == kind.value)
        if ip is not None:
            query = query.where(AccessEventOrm.ip == ip)
        if before_id is not None:
            query = query.where(AccessEventOrm.id < before_id)
        with session_scope() as session:
            return [to_entity(orm) for orm in session.execute(query).scalars()]

    def delete_before(self, cutoff: datetime) -> int:
        with session_scope() as session:
            return session.execute(delete(AccessEventOrm).where(AccessEventOrm.occurred_at < cutoff)).rowcount
