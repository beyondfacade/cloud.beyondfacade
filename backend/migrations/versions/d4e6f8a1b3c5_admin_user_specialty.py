"""전문가 전문 업종 — admin_user.specialty (예: 카페 · 부동산 · 노래방)

Revision ID: d4e6f8a1b3c5
Revises: c9d3e5f7a2b4
Create Date: 2026-10-12
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e6f8a1b3c5"
down_revision: Union[str, Sequence[str], None] = "c9d3e5f7a2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("admin_user", sa.Column("specialty", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("admin_user", "specialty")
