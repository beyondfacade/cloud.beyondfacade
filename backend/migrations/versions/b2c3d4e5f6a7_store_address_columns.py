"""store road_address + jibun_address (SGIS geocode queue)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-22 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("store", sa.Column("road_address", sa.String(), nullable=True))
    op.add_column("store", sa.Column("jibun_address", sa.String(), nullable=True))
    op.create_index(
        "ix_store_geocode_pending",
        "store",
        ["industry_id"],
        unique=False,
        postgresql_where=sa.text("lat IS NULL AND (road_address IS NOT NULL OR jibun_address IS NOT NULL)"),
    )


def downgrade() -> None:
    op.drop_index("ix_store_geocode_pending", table_name="store")
    op.drop_column("store", "jibun_address")
    op.drop_column("store", "road_address")
