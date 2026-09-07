from sqlalchemy import select

from apps.metric.adapter.outbound.orm_mappers.region_industry_metric_orm_mapper import (
    to_entity,
    to_orm,
)
from apps.metric.adapter.outbound.orms.region_industry_metric_orm import (
    RegionIndustryMetricOrm,
)
from apps.metric.app.ports.output.region_industry_metric_port import (
    RegionIndustryMetricRepositoryPort,
)
from apps.metric.domain.entities.region_industry_metric_entity import (
    RegionIndustryMetric,
)
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyRegionIndustryMetricRepository(RegionIndustryMetricRepositoryPort):
    def upsert(self, metrics: list[RegionIndustryMetric]) -> int:
        if not metrics:
            return 0
        with session_scope() as session:
            for metric in metrics:
                session.merge(to_orm(metric))
        return len(metrics)

    def list_by_industry_year(
        self, industry_id: str, year: int
    ) -> list[RegionIndustryMetric]:
        with session_scope() as session:
            rows = (
                session.execute(
                    select(RegionIndustryMetricOrm)
                    .where(
                        RegionIndustryMetricOrm.industry_id == industry_id,
                        RegionIndustryMetricOrm.year == year,
                    )
                    .order_by(RegionIndustryMetricOrm.region_code)
                )
                .scalars()
                .all()
            )
            return [to_entity(row) for row in rows]

    def find(
        self, region_code: str, industry_id: str, year: int
    ) -> RegionIndustryMetric | None:
        with session_scope() as session:
            orm = session.get(RegionIndustryMetricOrm, (region_code, industry_id, year))
            return None if orm is None else to_entity(orm)
