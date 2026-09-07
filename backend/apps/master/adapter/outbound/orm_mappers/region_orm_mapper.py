"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.master.domain.entities.region_entity import Region


def to_entity(orm: RegionOrm) -> Region:
    return Region(
        region_code=orm.region_code,
        district_code=orm.district_code,
        name=orm.name,
        geometry_ref=orm.geometry_ref,
    )
