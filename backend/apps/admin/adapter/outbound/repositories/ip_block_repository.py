from datetime import datetime

from sqlalchemy import delete, or_, select

from apps.admin.adapter.outbound.orm_mappers.ip_block_orm_mapper import apply_to_orm, to_entity, to_orm
from apps.admin.adapter.outbound.orms.ip_block_orm import IpBlockOrm
from apps.admin.app.ports.output.ip_block_port import IpBlockRepositoryPort
from apps.admin.domain.entities.ip_block_entity import IpBlock
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyIpBlockRepository(IpBlockRepositoryPort):
    def list_active(self, now: datetime) -> list[IpBlock]:
        with session_scope() as session:
            rows = session.execute(
                select(IpBlockOrm)
                .where(or_(IpBlockOrm.expires_at.is_(None), IpBlockOrm.expires_at > now))
                .order_by(IpBlockOrm.created_at.desc())
            ).scalars()
            return [to_entity(orm) for orm in rows]

    def get(self, ip: str) -> IpBlock | None:
        with session_scope() as session:
            orm = session.get(IpBlockOrm, ip)
            return to_entity(orm) if orm else None

    def save(self, block: IpBlock) -> None:
        with session_scope() as session:
            orm = session.get(IpBlockOrm, block.ip)
            if orm is None:
                session.add(to_orm(block))
            else:
                apply_to_orm(block, orm)

    def delete(self, ip: str) -> bool:
        with session_scope() as session:
            return session.execute(delete(IpBlockOrm).where(IpBlockOrm.ip == ip)).rowcount > 0

    def delete_expired(self, now: datetime) -> int:
        with session_scope() as session:
            return session.execute(
                delete(IpBlockOrm).where(IpBlockOrm.expires_at.is_not(None), IpBlockOrm.expires_at <= now)
            ).rowcount
