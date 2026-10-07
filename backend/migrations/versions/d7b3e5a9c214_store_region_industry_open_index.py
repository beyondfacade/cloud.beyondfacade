"""store 동·업종 영업 중 점포 부분 인덱스 — list_open 전용 (부하 테스트 H8)

부하 테스트 5차(10/7, 원격 k6): 점포 목록 쿼리가 DB 시간의 약 66%(6.8만 회, 평균 27.5ms — 한가할 때 11ms).
기존 인덱스는 (industry_id, district_code, …)뿐이라 업종 전체(카페 약 15만 행)를 읽고 동으로 걸렀다.
조건(동·업종·영업 중·좌표 있음)과 정렬(store_id)을 그대로 덮어 해당 동 점포만 정렬된 채로 읽는다.

Revision ID: d7b3e5a9c214
Revises: c4e8a2f6b913
Create Date: 2026-10-07
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "d7b3e5a9c214"
down_revision: Union[str, Sequence[str], None] = "c4e8a2f6b913"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_store_region_industry_open",
        "store",
        ["region_code", "industry_id", "store_id"],
        unique=False,
        postgresql_where=sa.text("close_date IS NULL AND lat IS NOT NULL AND lng IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_store_region_industry_open", table_name="store")
