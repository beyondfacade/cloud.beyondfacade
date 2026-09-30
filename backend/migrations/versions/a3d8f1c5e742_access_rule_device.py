"""화이트리스트·블랙리스트(access_rule)와 보안 이벤트의 디바이스 정보

Revision ID: a3d8f1c5e742
Revises: 9c4e2a7b1d35
Create Date: 2026-09-30 12:20:00.000000

IP 블랙리스트는 기존 ip_block이 맡는다. access_rule은 IP·대역 화이트리스트와 디바이스 화이트·블랙리스트.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3d8f1c5e742"
down_revision: Union[str, Sequence[str], None] = "9c4e2a7b1d35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "access_rule",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("policy", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("admin_user.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("policy", "target", "value", name="uq_access_rule_policy_target_value"),
    )
    op.add_column("access_event", sa.Column("device_id", sa.String(), nullable=True))
    op.add_column("access_event", sa.Column("user_agent", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("access_event", "user_agent")
    op.drop_column("access_event", "device_id")
    op.drop_table("access_rule")
