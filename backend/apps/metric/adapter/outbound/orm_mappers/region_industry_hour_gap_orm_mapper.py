"""Outbound Boundary Gate — RegionIndustryHourGap ↔ ORM 컬럼 (Repository ↔ DB 경계)."""

from apps.metric.adapter.outbound.orms.region_industry_hour_gap_quarter_orm import (
    RegionIndustryHourGapQuarterOrm,
)
from apps.metric.domain.entities.region_industry_hour_gap_entity import (
    RegionIndustryHourGap,
)

_COLUMNS: tuple[str, ...] = (
    "region_code",
    "industry_id",
    "year_quarter",
    "hour_band",
    "footfall_intensity",
    "sales_intensity",
    "gap",
)


def to_row(entity: RegionIndustryHourGap) -> dict:
    return {column: getattr(entity, column) for column in _COLUMNS}


def to_entity(orm: RegionIndustryHourGapQuarterOrm) -> RegionIndustryHourGap:
    return RegionIndustryHourGap(**{column: getattr(orm, column) for column in _COLUMNS})
