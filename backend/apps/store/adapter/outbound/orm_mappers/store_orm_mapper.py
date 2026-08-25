"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.store.domain.entities.store_entity import Store


def to_orm(entity: Store) -> StoreOrm:
    return StoreOrm(
        store_id=entity.store_id,
        name=entity.name,
        industry_id=entity.industry_id,
        district_code=entity.district_code,
        region_code=entity.region_code,
        subcategory_id=entity.subcategory_id,
        open_date=entity.open_date,
        close_date=entity.close_date,
        status_code=entity.status_code,
        status_name=entity.status_name,
        lat=entity.lat,
        lng=entity.lng,
        source_updated_at=entity.source_updated_at,
    )


def to_entity(orm: StoreOrm) -> Store:
    return Store(
        store_id=orm.store_id,
        name=orm.name,
        industry_id=orm.industry_id,
        district_code=orm.district_code,
        region_code=orm.region_code,
        subcategory_id=orm.subcategory_id,
        open_date=orm.open_date,
        close_date=orm.close_date,
        status_code=orm.status_code,
        status_name=orm.status_name,
        lat=orm.lat,
        lng=orm.lng,
        source_updated_at=orm.source_updated_at,
    )
