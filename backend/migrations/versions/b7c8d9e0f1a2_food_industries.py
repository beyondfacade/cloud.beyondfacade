"""음식 업종 8종 추가 + 인허가·상권분석 매핑

Revision ID: b7c8d9e0f1a2
Revises: e6f7a8b9c0d1
Create Date: 2026-09-28 00:00:00.000000

설계서 `docs/superpowers/specs/2026-09-28-industry-expansion-design.md` §3.

- industry 8행: 한식·중식·일식·양식·분식·치킨·호프주점 + 음식점(기타, 비노출). 시드(seed_master)와
  동일 내용을 여기서도 넣는 이유는 실DB가 시드 재실행 없이 alembic upgrade 만으로 정합해야 해서다.
  둘 다 멱등(ON CONFLICT DO NOTHING / merge).
- industry_source_code: 인허가 슬러그 general_restaurants 는 앵커 업종 restaurant_other 한 행만 등록한다.
  6업종을 각각 등록하면 수집기가 같은 50만 건을 6번 받는다. 건별 업종은 분류기가 정한다
  (`apps/store/domain/services/permit_industry_classifier.py`).
- seoul_commercial 7행: 한식 CS100001·중식 CS100002·일식 CS100003·양식 CS100004·치킨 CS100007·
  분식 CS100008·호프 CS100009.
- cafe↔CS100008(분식) 삭제: 분식이 독립 업종이 되면 카페 시간대 매출에 분식이 섞이면 안 된다.
  cafe↔CS100006(패스트푸드)은 휴게음식점 모집단 보정이라 유지 (교차검증 §3-2).

autogenerate 미사용 — 스키마 변경 없음, 데이터만.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDUSTRIES: tuple[tuple[str, str, str], ...] = (
    ("korean_food", "한식", "daily"),
    ("chinese_food", "중식", "daily"),
    ("japanese_food", "일식", "daily"),
    ("western_food", "양식", "daily"),
    ("snack", "분식", "daily"),
    ("chicken", "치킨", "daily"),
    ("pub", "호프·주점", "leisure"),
    ("restaurant_other", "음식점(기타)", "daily"),
)

_SOURCE_CODES: tuple[tuple[str, str, str], ...] = (
    ("restaurant_other", "mois_permit", "general_restaurants"),
    ("korean_food", "seoul_commercial", "CS100001"),
    ("chinese_food", "seoul_commercial", "CS100002"),
    ("japanese_food", "seoul_commercial", "CS100003"),
    ("western_food", "seoul_commercial", "CS100004"),
    ("chicken", "seoul_commercial", "CS100007"),
    ("snack", "seoul_commercial", "CS100008"),
    ("pub", "seoul_commercial", "CS100009"),
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for industry_id, name, demand_type in _INDUSTRIES:
        bind.execute(
            sa.text(
                "INSERT INTO industry (industry_id, name, demand_type) VALUES (:i, :n, :d) "
                "ON CONFLICT (industry_id) DO NOTHING"
            ),
            {"i": industry_id, "n": name, "d": demand_type},
        )
    for industry_id, source_system, code in _SOURCE_CODES:
        bind.execute(
            sa.text(
                "INSERT INTO industry_source_code (industry_id, source_system, code) VALUES (:i, :s, :c) "
                "ON CONFLICT (industry_id, source_system, code) DO NOTHING"
            ),
            {"i": industry_id, "s": source_system, "c": code},
        )
    bind.execute(
        sa.text(
            "DELETE FROM industry_source_code WHERE industry_id = 'cafe' "
            "AND source_system = 'seoul_commercial' AND code = 'CS100008'"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO industry_source_code (industry_id, source_system, code) "
            "VALUES ('cafe', 'seoul_commercial', 'CS100008') "
            "ON CONFLICT (industry_id, source_system, code) DO NOTHING"
        )
    )
    ids = tuple(i for i, _, _ in _INDUSTRIES)
    bind.execute(
        sa.text("DELETE FROM industry_source_code WHERE industry_id = ANY(:ids)"), {"ids": list(ids)}
    )
    bind.execute(sa.text("DELETE FROM store WHERE industry_id = ANY(:ids)"), {"ids": list(ids)})
    bind.execute(sa.text("DELETE FROM region_industry_metric WHERE industry_id = ANY(:ids)"), {"ids": list(ids)})
    bind.execute(sa.text("DELETE FROM industry WHERE industry_id = ANY(:ids)"), {"ids": list(ids)})
