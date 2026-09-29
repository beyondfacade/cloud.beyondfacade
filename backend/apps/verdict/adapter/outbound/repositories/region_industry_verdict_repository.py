from collections.abc import Iterable

from sqlalchemy import delete, select

from apps.verdict.adapter.outbound.orm_mappers.region_industry_verdict_orm_mapper import (
    to_entity,
    to_orm,
)
from apps.verdict.adapter.outbound.orms.region_industry_verdict_orm import RegionIndustryVerdictOrm
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    RegionIndustryVerdictRepositoryPort,
)
from apps.verdict.domain.entities.region_industry_verdict_entity import RegionIndustryVerdict
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyRegionIndustryVerdictRepository(RegionIndustryVerdictRepositoryPort):
    def upsert(self, verdicts: list[RegionIndustryVerdict]) -> int:
        if not verdicts:
            return 0
        with session_scope() as session:
            for verdict in verdicts:
                session.merge(to_orm(verdict))
        return len(verdicts)

    def list_by_industry(self, industry_id: str) -> list[RegionIndustryVerdict]:
        with session_scope() as session:
            rows = session.execute(
                select(RegionIndustryVerdictOrm)
                .where(RegionIndustryVerdictOrm.industry_id == industry_id)
                .order_by(RegionIndustryVerdictOrm.region_code)
            ).scalars().all()
            return [to_entity(row) for row in rows]

    def list_by_region(self, region_code: str) -> list[RegionIndustryVerdict]:
        with session_scope() as session:
            rows = session.execute(
                select(RegionIndustryVerdictOrm)
                .where(RegionIndustryVerdictOrm.region_code == region_code)
                .order_by(RegionIndustryVerdictOrm.industry_id)
            ).scalars().all()
            return [to_entity(row) for row in rows]

    def find(self, region_code: str, industry_id: str) -> RegionIndustryVerdict | None:
        with session_scope() as session:
            orm = session.get(RegionIndustryVerdictOrm, (region_code, industry_id))
            return None if orm is None else to_entity(orm)

    def delete_other_industries(self, keep_industry_ids: Iterable[str]) -> int:
        with session_scope() as session:
            result = session.execute(
                delete(RegionIndustryVerdictOrm).where(RegionIndustryVerdictOrm.industry_id.not_in(list(keep_industry_ids)))
            )
            return result.rowcount
