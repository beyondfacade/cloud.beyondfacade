"""Driven Adapter — master BC 조회 (cross-BC 접근은 게이트웨이 안에서만)."""

from sqlalchemy import select

from apps.finance.app.ports.output.finance_port import MasterLookupPort
from apps.master.adapter.outbound.orms.industry_orm import IndustryOrm
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope


class MasterLookupGateway(MasterLookupPort):
    def district_of_region(self, region_code: str) -> str | None:
        with session_scope() as session:
            return session.execute(
                select(RegionOrm.district_code).where(RegionOrm.region_code == region_code)
            ).scalar_one_or_none()

    def industry_exists(self, industry_id: str) -> bool:
        with session_scope() as session:
            return session.get(IndustryOrm, industry_id) is not None
