"""판정 원천 컬럼 region_industry_verdict.basis

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-09-29 12:00:00.000000

설계서 `docs/superpowers/specs/2026-09-29-industry-specific-signals-design.md` §9-1.
permit(인허가) · proxy(담배소매인 대리) · aggregate(상권분석 집계). 기존 행은 전부 인허가 원천이라 기본값이 참값이다.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "region_industry_verdict",
        sa.Column("basis", sa.String(length=12), nullable=False, server_default="permit"),
    )


def downgrade() -> None:
    op.drop_column("region_industry_verdict", "basis")
