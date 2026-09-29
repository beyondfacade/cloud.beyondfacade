"""Driven Adapter — 전 행정동 이름 + 최신 분기 동네 유형(region_profile_quarter). 프로필이 없는 동은 유형 None."""

from sqlalchemy import and_, func, select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.metric.adapter.outbound.orms.region_profile_quarter_orm import RegionProfileQuarterOrm
from apps.verdict.app.dtos.region_industry_verdict_dto import RegionInfo
from apps.verdict.app.ports.output.region_industry_verdict_port import RegionCatalogPort
from core.matrix.grid_oracle_database_manager import session_scope


class RegionCatalogGateway(RegionCatalogPort):
    def regions(self) -> list[RegionInfo]:
        P = RegionProfileQuarterOrm
        with session_scope() as session:
            latest = select(P.region_code, func.max(P.year_quarter).label("yq")).group_by(P.region_code).subquery()
            rows = session.execute(
                select(RegionOrm.region_code, RegionOrm.name, P.neighborhood_type)
                .join(latest, latest.c.region_code == RegionOrm.region_code, isouter=True)
                .join(P, and_(P.region_code == latest.c.region_code, P.year_quarter == latest.c.yq), isouter=True)
                .order_by(RegionOrm.region_code)
            ).all()
        return [RegionInfo(code, name, neighborhood_type) for code, name, neighborhood_type in rows]
