"""보안 동작 스위치 — 자동 방어 켜기·끄기

Revision ID: 9c4e2a7b1d35
Revises: 7b1d4e9a2c60
Create Date: 2026-09-30 12:10:00.000000

행이 없으면 코드의 기본값(자동 방어 켜짐)을 쓴다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9c4e2a7b1d35"
down_revision: Union[str, Sequence[str], None] = "7b1d4e9a2c60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "security_setting",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("admin_user.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("security_setting")
