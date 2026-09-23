"""Outbound Boundary Gate — entity ↔ ORM 컬럼 (Repository ↔ DB 경계).

읽기 경로는 조회 라우터(v0.29.0)와 함께 열었다. 적재와 조회가 레포지토리는 둘이지만
경계 변환은 여기 한 벌만 둔다 — 컬럼이 늘 때 한쪽만 고치는 자리를 만들지 않는다.
"""

from apps.neighborhood.adapter.outbound.orms.region_commerce_change_orm import (
    RegionCommerceChangeOrm,
)
from apps.neighborhood.domain.entities.region_commerce_change_entity import RegionCommerceChange


def to_row(entity: RegionCommerceChange) -> dict:
    return {
        "adstrd_code": entity.adstrd_code,
        "year_quarter": entity.year_quarter,
        "change_code": entity.change_code,
        "change_name": entity.change_name,
        "operating_months": entity.operating_months,
        "closed_months": entity.closed_months,
        "region_code": entity.region_code,
    }


def to_entity(orm: RegionCommerceChangeOrm) -> RegionCommerceChange:
    return RegionCommerceChange(
        adstrd_code=orm.adstrd_code,
        year_quarter=orm.year_quarter,
        change_code=orm.change_code,
        change_name=orm.change_name,
        operating_months=orm.operating_months,
        closed_months=orm.closed_months,
        region_code=orm.region_code,
    )
