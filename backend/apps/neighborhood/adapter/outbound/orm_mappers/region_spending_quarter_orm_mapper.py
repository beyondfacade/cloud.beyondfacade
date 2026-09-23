"""Outbound Boundary Gate — entity → ORM 컬럼 (Repository ↔ DB 경계).

읽기 경로(ORM → entity)는 라우터가 생기는 후속 범위에서 추가한다.
"""

from apps.neighborhood.domain.entities.region_spending_quarter_entity import RegionSpendingQuarter


def to_row(entity: RegionSpendingQuarter) -> dict:
    return {
        "adstrd_code": entity.adstrd_code,
        "year_quarter": entity.year_quarter,
        "spending_category": entity.spending_category,
        "region_code": entity.region_code,
        "amount": entity.amount,
    }
