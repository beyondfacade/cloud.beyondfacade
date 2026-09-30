"""관리자 조치 감사 로그 테이블

Revision ID: a6b7c8d9e0f1
Revises: f4a5b6c7d8e9
Create Date: 2026-09-30 10:00:00.000000

IP 차단·계정 변경·수동 실행 같은 관리자 조치를 '누가 언제 무엇을' 남긴다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_audit",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("admin_user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_username", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("detail", sa.String(), nullable=False),
        sa.Column("ip", sa.String(), nullable=True),
    )
    op.create_index("ix_admin_audit_occurred_at", "admin_audit", ["occurred_at"])
    op.create_index("ix_admin_audit_action_id", "admin_audit", ["action", "id"])


def downgrade() -> None:
    op.drop_index("ix_admin_audit_action_id", table_name="admin_audit")
    op.drop_index("ix_admin_audit_occurred_at", table_name="admin_audit")
    op.drop_table("admin_audit")
