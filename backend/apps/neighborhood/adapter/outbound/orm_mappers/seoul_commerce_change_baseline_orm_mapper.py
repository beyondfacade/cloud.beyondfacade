"""Outbound Boundary Gate — entity → ORM 컬럼 (Repository ↔ DB 경계).

읽기 경로(ORM → entity)는 라우터가 생기는 후속 범위에서 추가한다.
"""

from apps.neighborhood.domain.entities.seoul_commerce_change_baseline_entity import (
    SeoulCommerceChangeBaseline,
)


def to_row(entity: SeoulCommerceChangeBaseline) -> dict:
    return {
        "year_quarter": entity.year_quarter,
        "seoul_operating_months": entity.seoul_operating_months,
        "seoul_closed_months": entity.seoul_closed_months,
    }
