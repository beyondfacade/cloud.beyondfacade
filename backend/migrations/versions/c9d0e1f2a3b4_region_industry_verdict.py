"""판정 테이블 region_industry_verdict

Revision ID: c9d0e1f2a3b4
Revises: b7c8d9e0f1a2
Create Date: 2026-09-29 00:00:00.000000

설계서 `docs/superpowers/specs/2026-09-28-verdict-card-design.md` §4-3.
동×업종당 1행(판정 코드·켜진 개수·신호 JSON·산출 시각). 새벽 배치 `build_verdicts`가 재생성한다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "region_industry_verdict",
        sa.Column("region_code", sa.String(), sa.ForeignKey("region.region_code"), primary_key=True),
        sa.Column("industry_id", sa.String(), sa.ForeignKey("industry.industry_id"), primary_key=True),
        sa.Column("verdict_code", sa.String(length=12), nullable=False),
        sa.Column("strong_count", sa.SmallInteger(), nullable=False),
        sa.Column("on_count", sa.SmallInteger(), nullable=False),
        sa.Column("signals_json", sa.Text(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_region_industry_verdict_industry", "region_industry_verdict", ["industry_id"])


def downgrade() -> None:
    op.drop_index("ix_region_industry_verdict_industry", table_name="region_industry_verdict")
    op.drop_table("region_industry_verdict")
