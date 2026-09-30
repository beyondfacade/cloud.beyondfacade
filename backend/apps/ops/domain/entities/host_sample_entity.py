from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class HostSample:
    """설비 지표 1분 표본 — 추세 차트용이라 비율(%)로 정규화해 둔다. 조회 실패 항목은 None."""

    sampled_at: datetime
    cpu_percent: float | None = None
    load1: float | None = None
    memory_percent: float | None = None
    swap_percent: float | None = None
    disk_percent: float | None = None
    gpu_util_percent: float | None = None
    gpu_memory_percent: float | None = None
    gpu_temp_c: float | None = None
