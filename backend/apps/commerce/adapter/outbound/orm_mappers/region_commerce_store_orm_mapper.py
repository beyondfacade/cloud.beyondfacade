"""Outbound Boundary Gate — entity → ORM 컬럼 (Repository ↔ DB 경계)."""

from apps.commerce.domain.entities.region_commerce_store_entity import RegionCommerceStore


def to_row(entity: RegionCommerceStore) -> dict:
    return {
        "adstrd_code": entity.adstrd_code,
        "service_industry_code": entity.service_industry_code,
        "year_quarter": entity.year_quarter,
        "region_code": entity.region_code,
        "store_count": entity.store_count,
        "similar_industry_store_count": entity.similar_industry_store_count,
        "open_rate": entity.open_rate,
        "open_store_count": entity.open_store_count,
        "close_rate": entity.close_rate,
        "close_store_count": entity.close_store_count,
        "franchise_store_count": entity.franchise_store_count,
    }
