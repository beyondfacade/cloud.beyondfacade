"""Driven Adapter — rent BC(R-ONE 임대동향)의 권역(`region_level=2`) 최신 분기 임대료."""

from sqlalchemy import select

from apps.finance.app.dtos.finance_dto import RentBasis
from apps.finance.app.ports.output.finance_port import RentFactsPort
from apps.rent.adapter.outbound.orms.rent_price_orm import RentPriceOrm
from core.matrix.grid_oracle_database_manager import session_scope

_ZONE_LEVEL = 2


class RentFactsGateway(RentFactsPort):
    def latest_zone_rent(self, zone_path: str) -> RentBasis | None:
        with session_scope() as session:
            latest = session.execute(
                select(RentPriceOrm.period)
                .where(RentPriceOrm.region_path == zone_path, RentPriceOrm.region_level == _ZONE_LEVEL)
                .order_by(RentPriceOrm.period.desc())
                .limit(1)
            ).scalar_one_or_none()
            if latest is None:
                return None
            rows = session.execute(
                select(RentPriceOrm.building_type, RentPriceOrm.rent_per_m2).where(
                    RentPriceOrm.region_path == zone_path,
                    RentPriceOrm.region_level == _ZONE_LEVEL,
                    RentPriceOrm.period == latest,
                )
            ).all()
        by_type = {building_type: rent for building_type, rent in rows}
        return RentBasis(
            region_path=zone_path,
            period=latest,
            medium_large_per_m2=by_type.get("medium_large"),
            small_per_m2=by_type.get("small"),
        )
