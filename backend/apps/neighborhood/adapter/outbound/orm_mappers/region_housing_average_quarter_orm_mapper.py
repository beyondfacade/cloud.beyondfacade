"""Outbound Boundary Gate — entity → ORM 컬럼 (Repository ↔ DB 경계).

읽기 경로(ORM → entity)는 라우터가 생기는 후속 범위에서 추가한다.
"""

from apps.neighborhood.domain.entities.region_housing_average_quarter_entity import (
    RegionHousingAverageQuarter,
)


def to_row(entity: RegionHousingAverageQuarter) -> dict:
    return {
        "adstrd_code": entity.adstrd_code,
        "year_quarter": entity.year_quarter,
        "region_code": entity.region_code,
        "avg_area_m2": entity.avg_area_m2,
        "avg_price": entity.avg_price,
    }
