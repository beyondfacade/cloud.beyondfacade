"""region_profile_quarter 4블록 시간당 강도 컬럼 4개

Revision ID: e6f7a8b9c0d1
Revises: c5d6e7f8a9b0
Create Date: 2026-09-23 23:40:00.000000

패널의 "하루가 어떻게 흐르나" 막대 4개(아침·낮·저녁·밤)의 원천이다. 프로필 배치가 4분기 평활한
시간대 6구간에서 블록 강도를 한 번만 계산해 넣는다 — 화면이 원값으로 시간당 보정을 다시 하면
두 곳 중 하나가 언젠가 틀린다 (무대 설계서 `docs/superpowers/specs/2026-09-23-map-stage-design.md` §5-1).
nullable 추가만이라 배치 재실행 전에는 NULL이고, 응답은 넷이 다 있을 때만 `block_intensities`를 준다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = ("block_morning", "block_day", "block_evening", "block_night")


def upgrade() -> None:
    """Upgrade schema."""
    for column in _COLUMNS:
        op.add_column("region_profile_quarter", sa.Column(column, sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for column in reversed(_COLUMNS):
        op.drop_column("region_profile_quarter", column)
