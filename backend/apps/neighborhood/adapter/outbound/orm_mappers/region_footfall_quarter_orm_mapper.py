"""Outbound Boundary Gate — entity → ORM 컬럼 (Repository ↔ DB 경계).

읽기 경로(ORM → entity)는 라우터가 생기는 후속 범위에서 추가한다.
"""

from apps.neighborhood.domain.entities.region_footfall_quarter_entity import RegionFootfallQuarter


def to_row(entity: RegionFootfallQuarter) -> dict:
    return {
        "adstrd_code": entity.adstrd_code,
        "year_quarter": entity.year_quarter,
        "dim_type": entity.dim_type,
        "dim_key": entity.dim_key,
        "region_code": entity.region_code,
        "headcount": entity.headcount,
    }
