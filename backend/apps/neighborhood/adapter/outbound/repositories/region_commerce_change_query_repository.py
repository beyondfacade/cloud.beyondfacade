from sqlalchemy import select

from apps.neighborhood.adapter.outbound.orm_mappers.region_commerce_change_orm_mapper import (
    to_entity,
)
from apps.neighborhood.adapter.outbound.orms.region_commerce_change_orm import (
    RegionCommerceChangeOrm,
)
from apps.neighborhood.app.ports.output.region_commerce_change_query_port import (
    RegionCommerceChangeQueryPort,
)
from apps.neighborhood.domain.entities.region_commerce_change_entity import (
    RegionCommerceChange,
)
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyRegionCommerceChangeQueryRepository(RegionCommerceChangeQueryPort):
    def find(self, region_code: str, year_quarter: str) -> RegionCommerceChange | None:
        with session_scope() as session:
            orm = session.execute(
                select(RegionCommerceChangeOrm).where(
                    RegionCommerceChangeOrm.region_code == region_code,
                    RegionCommerceChangeOrm.year_quarter == year_quarter,
                )
            ).scalar_one_or_none()
            return None if orm is None else to_entity(orm)

    def find_latest(self, region_code: str) -> RegionCommerceChange | None:
        with session_scope() as session:
            orm = session.execute(
                select(RegionCommerceChangeOrm)
                .where(RegionCommerceChangeOrm.region_code == region_code)
                .order_by(RegionCommerceChangeOrm.year_quarter.desc())
                .limit(1)
            ).scalar_one_or_none()
            return None if orm is None else to_entity(orm)
