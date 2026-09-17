"""Driven Adapter — region 마스터 존재 확인 (cross-BC 접근은 어댑터 레이어에서만)."""

from apps.childcare.app.ports.output.childcare_center_port import RegionCatalogPort
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope


class RegionCatalogGateway(RegionCatalogPort):
    def exists(self, region_code: str) -> bool:
        with session_scope() as session:
            return session.get(RegionOrm, region_code) is not None
