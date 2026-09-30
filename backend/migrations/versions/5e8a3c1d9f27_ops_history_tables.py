"""설비 지표 표본·LLM 호출 결과 테이블

Revision ID: 5e8a3c1d9f27
Revises: a6b7c8d9e0f1
Create Date: 2026-09-30 11:00:00.000000

설비실 추세 차트(1분 표본, 8일 보존)와 헬스케어실 폴백률·오류율(호출 시도마다 1행).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5e8a3c1d9f27"
down_revision: Union[str, Sequence[str], None] = "a6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_METRICS = (
    "cpu_percent",
    "load1",
    "memory_percent",
    "swap_percent",
    "disk_percent",
    "gpu_util_percent",
    "gpu_memory_percent",
    "gpu_temp_c",
)


def upgrade() -> None:
    op.create_table(
        "host_metric_sample",
        sa.Column("sampled_at", sa.DateTime(timezone=True), primary_key=True),
        *[sa.Column(name, sa.Float(), nullable=True) for name in _METRICS],
    )
    op.create_table(
        "llm_call_event",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("error_kind", sa.String(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
    )
    op.create_index("ix_llm_call_event_occurred_at", "llm_call_event", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_call_event_occurred_at", table_name="llm_call_event")
    op.drop_table("llm_call_event")
    op.drop_table("host_metric_sample")
