"""Outbound Boundary Gate — entity ↔ ORM 컬럼 (Repository ↔ DB 경계).

읽기 경로는 상권 변화 상세 응답(v0.32.0)이 서울 평균을 동봉하면서 열었다. 적재·조회 레포지토리가
둘이어도 경계 변환은 여기 한 벌이다.
"""

from apps.neighborhood.adapter.outbound.orms.seoul_commerce_change_baseline_orm import (
    SeoulCommerceChangeBaselineOrm,
)
from apps.neighborhood.domain.entities.seoul_commerce_change_baseline_entity import (
    SeoulCommerceChangeBaseline,
)


def to_row(entity: SeoulCommerceChangeBaseline) -> dict:
    return {
        "year_quarter": entity.year_quarter,
        "seoul_operating_months": entity.seoul_operating_months,
        "seoul_closed_months": entity.seoul_closed_months,
    }


def to_entity(orm: SeoulCommerceChangeBaselineOrm) -> SeoulCommerceChangeBaseline:
    return SeoulCommerceChangeBaseline(
        year_quarter=orm.year_quarter,
        seoul_operating_months=orm.seoul_operating_months,
        seoul_closed_months=orm.seoul_closed_months,
    )
