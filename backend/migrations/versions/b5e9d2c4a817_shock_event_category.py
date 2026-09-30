"""shock_event 이벤트 유형(category) — 유사 사례 비교

Revision ID: b5e9d2c4a817
Revises: a3d8f1c5e742
Create Date: 2026-09-30 16:10:00.000000

같은 유형의 지난 이벤트를 지금 이벤트의 참고 사례로 잇는다. 세부 국면(거리두기 단계 조정 등)은 NULL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5e9d2c4a817"
down_revision: Union[str, Sequence[str], None] = "a3d8f1c5e742"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shock_event", sa.Column("category", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("shock_event", "category")
