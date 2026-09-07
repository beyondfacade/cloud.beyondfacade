"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.metric.adapter.outbound.orms.region_industry_metric_orm import (
    RegionIndustryMetricOrm,
)
from apps.metric.domain.entities.region_industry_metric_entity import (
    RegionIndustryMetric,
)


def to_orm(entity: RegionIndustryMetric) -> RegionIndustryMetricOrm:
    return RegionIndustryMetricOrm(
        region_code=entity.region_code,
        industry_id=entity.industry_id,
        year=entity.year,
        store_count=entity.store_count,
        open_count=entity.open_count,
        close_count=entity.close_count,
        closure_rate=entity.closure_rate,
        growth_rate=entity.growth_rate,
    )


def to_entity(orm: RegionIndustryMetricOrm) -> RegionIndustryMetric:
    return RegionIndustryMetric(
        region_code=orm.region_code,
        industry_id=orm.industry_id,
        year=orm.year,
        store_count=orm.store_count,
        open_count=orm.open_count,
        close_count=orm.close_count,
        closure_rate=orm.closure_rate,
        growth_rate=orm.growth_rate,
    )
