"""아파트 매매 건수 보조 테이블 apt_trade_count

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-09-29 18:00:00.000000

업종 특화 신호 설계서 §11-3. 자치구×법정동×월 건수만.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "apt_trade_count",
        sa.Column("district_code", sa.String(), sa.ForeignKey("district.district_code"), primary_key=True),
        sa.Column("legal_dong", sa.String(length=40), primary_key=True),
        sa.Column("deal_ym", sa.String(length=6), primary_key=True),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("apt_trade_count")
