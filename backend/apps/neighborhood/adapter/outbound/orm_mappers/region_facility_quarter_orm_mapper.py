"""Outbound Boundary Gate — entity → ORM 컬럼 (Repository ↔ DB 경계).

읽기 경로(ORM → entity)는 라우터가 생기는 후속 범위에서 추가한다.
"""

from apps.neighborhood.domain.entities.region_facility_quarter_entity import RegionFacilityQuarter


def to_row(entity: RegionFacilityQuarter) -> dict:
    return {
        "adstrd_code": entity.adstrd_code,
        "year_quarter": entity.year_quarter,
        "facility_type": entity.facility_type,
        "region_code": entity.region_code,
        "facility_count": entity.facility_count,
    }
