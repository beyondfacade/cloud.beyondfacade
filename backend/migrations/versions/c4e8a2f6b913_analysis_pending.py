"""대기 분석 장부 analysis_pending — 프로세스 메모리 dict(_PENDING)를 Postgres로

Revision ID: c4e8a2f6b913
Revises: b3f7d1e9a264
Create Date: 2026-10-07 00:00:00.000000

워커를 늘리면 POST /analysis와 GET /analysis/{id}/events가 다른 워커로 가 404가 난다(부하 테스트 H5, BE v0.92.0).
region·industry 마스터에 FK로 붙는다(ERD §13). 30분 지난 행은 저장소 save가 함께 지운다(크론 없음).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8a2f6b913"
down_revision: Union[str, Sequence[str], None] = "b3f7d1e9a264"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_pending",
        sa.Column("analysis_id", sa.String(32), primary_key=True),
        sa.Column(
            "region_code",
            sa.String(),
            sa.ForeignKey("region.region_code", name="fk_analysis_pending_region"),
            nullable=False,
        ),
        sa.Column(
            "industry_id",
            sa.String(),
            sa.ForeignKey("industry.industry_id", name="fk_analysis_pending_industry"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("budget", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_analysis_pending_created_at", "analysis_pending", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_analysis_pending_created_at", table_name="analysis_pending")
    op.drop_table("analysis_pending")
