"""Outbound Boundary Gate — ORM → entity 변환 (Repository ↔ DB 경계)."""

from apps.convenience.adapter.outbound.orms.convenience_store_orm import ConvenienceStoreOrm
from apps.convenience.domain.entities.convenience_store_entity import ConvenienceStore


def to_entity(orm: ConvenienceStoreOrm) -> ConvenienceStore:
    return ConvenienceStore(
        store_id=orm.store_id,
        name=orm.name,
        branch_name=orm.branch_name,
        brand=orm.brand,
        region_code=orm.region_code,
        lat=orm.lat,
        lng=orm.lng,
        road_address=orm.road_address,
        jibun_address=orm.jibun_address,
        source_stdr_ym=orm.source_stdr_ym,
    )
