"""프로필 사진 — admin_user.avatar_version + admin_user_avatar(바이트)

Revision ID: f6a8b1c3d5e7
Revises: e5f7a9b1c3d6
Create Date: 2026-10-12
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a8b1c3d5e7"
down_revision: Union[str, Sequence[str], None] = "e5f7a9b1c3d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("admin_user", sa.Column("avatar_version", sa.Integer(), nullable=True))
    op.create_table(
        "admin_user_avatar",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("admin_user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("admin_user_avatar")
    op.drop_column("admin_user", "avatar_version")
