from sqlalchemy import select

from apps.master.adapter.outbound.orm_mappers.region_orm_mapper import to_entity
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.master.app.ports.output.region_port import RegionRepositoryPort
from apps.master.domain.entities.region_entity import Region
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyRegionRepository(RegionRepositoryPort):
    def list_regions(self) -> list[Region]:
        with session_scope() as session:
            rows = (
                session.execute(select(RegionOrm).order_by(RegionOrm.region_code))
                .scalars()
                .all()
            )
            return [to_entity(row) for row in rows]

    def find(self, region_code: str) -> Region | None:
        with session_scope() as session:
            orm = session.get(RegionOrm, region_code)
            return None if orm is None else to_entity(orm)
