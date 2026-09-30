from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class HostMetricSampleOrm(OrmBase):
    """설비 지표 1분 표본 — sample_host_metrics 크론이 쌓고 8일 지나면 지운다."""

    __tablename__ = "host_metric_sample"

    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    cpu_percent: Mapped[float | None]
    load1: Mapped[float | None]
    memory_percent: Mapped[float | None]
    swap_percent: Mapped[float | None]
    disk_percent: Mapped[float | None]
    gpu_util_percent: Mapped[float | None]
    gpu_memory_percent: Mapped[float | None]
    gpu_temp_c: Mapped[float | None]
