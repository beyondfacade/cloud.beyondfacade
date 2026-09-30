from dataclasses import dataclass, field
from datetime import datetime

from apps.ops.domain.services.usage_series import CallOutcomes, UsagePoint


@dataclass(frozen=True)
class OpsActorDto:
    """조치를 한 관리자 — admin BC 타입을 들이지 않고 감사에 필요한 값만."""

    id: int
    username: str
    ip: str | None


@dataclass(frozen=True)
class HostPointDto:
    t: datetime
    cpu_percent: float | None
    load1: float | None
    memory_percent: float | None
    swap_percent: float | None
    disk_percent: float | None
    gpu_util_percent: float | None
    gpu_memory_percent: float | None
    gpu_temp_c: float | None


@dataclass(frozen=True)
class HostHistoryDto:
    generated_at: datetime
    hours: int
    bucket_seconds: int
    points: list[HostPointDto] = field(default_factory=list)


@dataclass(frozen=True)
class UsageSeriesDto:
    generated_at: datetime
    hours: int
    bucket_hours: int
    points: list[UsagePoint]
    outcomes: CallOutcomes
    by_hour: list[int]  # 한국 시각 0~23시별 분석 건수


@dataclass(frozen=True)
class CollectorLogDto:
    key: str
    log_file: str
    lines: list[str]  # 비밀값을 가린 뒤
    last_run_at: datetime | None
    running: bool


@dataclass(frozen=True)
class CollectorRunDto:
    key: str
    started_at: datetime
