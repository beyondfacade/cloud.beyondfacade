"""Outbound Boundary Gate — RegionProfile ↔ ORM 컬럼 (Repository ↔ DB 경계)."""

from apps.metric.adapter.outbound.orms.region_profile_quarter_orm import (
    RegionProfileQuarterOrm,
)
from apps.metric.domain.entities.region_profile_entity import RegionProfile

_COLUMNS: tuple[str, ...] = (
    "region_code",
    "year_quarter",
    "neighborhood_type",
    "type_reason",
    "time_label",
    "peak_block",
    "trough_block",
    "worker_resident_ratio",
    "weekend_index",
    "night_index",
    "footfall_20s_share",
    "fnb_share",
    "facility_total",
    "resident_total",
    "block_morning",
    "block_day",
    "block_evening",
    "block_night",
)


def to_row(entity: RegionProfile) -> dict:
    return {column: getattr(entity, column) for column in _COLUMNS}


def to_entity(orm: RegionProfileQuarterOrm) -> RegionProfile:
    return RegionProfile(**{column: getattr(orm, column) for column in _COLUMNS})
