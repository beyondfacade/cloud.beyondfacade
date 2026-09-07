"""Driven Adapter — industry 마스터 존재 확인 (cross-BC 접근은 어댑터 레이어에서만)."""

from apps.master.adapter.outbound.orms.industry_orm import IndustryOrm
from apps.metric.app.ports.output.region_industry_metric_port import IndustryCatalogPort
from core.matrix.grid_oracle_database_manager import session_scope


class IndustryCatalogGateway(IndustryCatalogPort):
    def exists(self, industry_id: str) -> bool:
        with session_scope() as session:
            return session.get(IndustryOrm, industry_id) is not None
