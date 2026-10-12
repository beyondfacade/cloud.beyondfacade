"""전문가 상담 — 시간당 요금(admin_user.hourly_rate)과 상담 구매 기록(chat_consultation)

산 상담 시간이 끝나기 전까지 그 전문가는 '대화 중'이라 다른 회원이 1:1을 걸 수 없다.

Revision ID: c9d3e5f7a2b4
Revises: b8c2d4e6f1a3
Create Date: 2026-10-12
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d3e5f7a2b4"
down_revision: Union[str, Sequence[str], None] = "b8c2d4e6f1a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("admin_user", sa.Column("hourly_rate", sa.Integer(), nullable=True))
    op.create_table(
        "chat_consultation",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("viewer_id", sa.Integer(), sa.ForeignKey("admin_user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expert_id", sa.Integer(), sa.ForeignKey("admin_user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hours", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_consultation_expert_ends_at", "chat_consultation", ["expert_id", "ends_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_consultation_expert_ends_at", table_name="chat_consultation")
    op.drop_table("chat_consultation")
    op.drop_column("admin_user", "hourly_rate")
