from sqlalchemy import select

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


def _to_entity(orm: RegionCommerceChangeOrm) -> RegionCommerceChange:
    return RegionCommerceChange(
        adstrd_code=orm.adstrd_code,
        year_quarter=orm.year_quarter,
        change_code=orm.change_code,
        change_name=orm.change_name,
        operating_months=orm.operating_months,
        closed_months=orm.closed_months,
        region_code=orm.region_code,
    )


class SqlAlchemyRegionCommerceChangeQueryRepository(RegionCommerceChangeQueryPort):
    def latest_quarter(self) -> str | None:
        with session_scope() as session:
            return session.execute(
                select(RegionCommerceChangeOrm.year_quarter)
                .order_by(RegionCommerceChangeOrm.year_quarter.desc())
                .limit(1)
            ).scalar_one_or_none()

    def list_by_quarter(self, year_quarter: str) -> list[RegionCommerceChange]:
        with session_scope() as session:
            rows = (
                session.execute(
                    select(RegionCommerceChangeOrm)
                    .where(
                        RegionCommerceChangeOrm.year_quarter == year_quarter,
                        # 원천에만 있는 옛 행정동 3개는 지도에 올릴 수 없다
                        RegionCommerceChangeOrm.region_code.is_not(None),
                    )
                    .order_by(RegionCommerceChangeOrm.region_code)
                )
                .scalars()
                .all()
            )
            return [_to_entity(row) for row in rows]
