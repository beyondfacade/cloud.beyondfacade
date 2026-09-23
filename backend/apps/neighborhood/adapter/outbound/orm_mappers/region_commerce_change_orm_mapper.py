"""Outbound Boundary Gate — entity → ORM 컬럼 (Repository ↔ DB 경계).

읽기 경로(ORM → entity)는 라우터가 생기는 후속 범위에서 추가한다.
"""

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
