"""관리자 계정·세션·보안 이벤트·IP 차단 테이블

Revision ID: f4a5b6c7d8e9
Revises: e1f2a3b4c5d6
Create Date: 2026-09-29 21:30:00.000000

관리자 페이지 3종(보안감사팀·헬스케어실·설비실)의 인증과 보안감사 데이터.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_user",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "admin_session",
        sa.Column("token_hash", sa.String(), primary_key=True),
        sa.Column(
            "admin_user_id", sa.Integer(), sa.ForeignKey("admin_user.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip", sa.String(), nullable=True),
    )
    op.create_index("ix_admin_session_admin_user_id", "admin_session", ["admin_user_id"])
    op.create_table(
        "access_event",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("ip", sa.String(), nullable=True),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column(
            "admin_user_id", sa.Integer(), sa.ForeignKey("admin_user.id", ondelete="SET NULL"), nullable=True
        ),
    )
    op.create_index("ix_access_event_occurred_at", "access_event", ["occurred_at"])
    op.create_index("ix_access_event_kind_ip_time", "access_event", ["kind", "ip", "occurred_at"])
    op.create_table(
        "ip_block",
        sa.Column("ip", sa.String(), primary_key=True),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by", sa.Integer(), sa.ForeignKey("admin_user.id", ondelete="SET NULL"), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_table("ip_block")
    op.drop_index("ix_access_event_kind_ip_time", table_name="access_event")
    op.drop_index("ix_access_event_occurred_at", table_name="access_event")
    op.drop_table("access_event")
    op.drop_index("ix_admin_session_admin_user_id", table_name="admin_session")
    op.drop_table("admin_session")
    op.drop_table("admin_user")
