"""Driven Adapter — industry 마스터에서 판정 대상 업종만 (EXCLUDED_INDUSTRIES 제외)."""

from collections.abc import Iterable

from sqlalchemy import select

from apps.master.adapter.outbound.orms.industry_orm import IndustryOrm
from apps.verdict.app.dtos.region_industry_verdict_dto import JudgedIndustry
from apps.verdict.app.ports.output.region_industry_verdict_port import IndustryCatalogPort
from apps.verdict.domain.entities.region_industry_verdict_entity import EXCLUDED_INDUSTRIES
from core.matrix.grid_oracle_database_manager import session_scope


class IndustryCatalogGateway(IndustryCatalogPort):
    def judged_industries(self) -> list[JudgedIndustry]:
        with session_scope() as session:
            rows = session.execute(
                select(IndustryOrm.industry_id, IndustryOrm.name)
                .where(IndustryOrm.industry_id.not_in(EXCLUDED_INDUSTRIES))
                .order_by(IndustryOrm.industry_id)
            ).all()
        return [JudgedIndustry(industry_id, name) for industry_id, name in rows]

    def named_industries(self, industry_ids: Iterable[str]) -> list[JudgedIndustry]:
        ids = list(industry_ids)
        with session_scope() as session:
            rows = session.execute(
                select(IndustryOrm.industry_id, IndustryOrm.name)
                .where(IndustryOrm.industry_id.in_(ids))
                .order_by(IndustryOrm.industry_id)
            ).all()
        return [JudgedIndustry(industry_id, name) for industry_id, name in rows]
