from datetime import datetime

from pydantic import BaseModel


class HostPointResponse(BaseModel):
    t: datetime
    cpu_percent: float | None
    load1: float | None
    memory_percent: float | None
    swap_percent: float | None
    disk_percent: float | None
    gpu_util_percent: float | None
    gpu_memory_percent: float | None
    gpu_temp_c: float | None


class HostHistoryResponse(BaseModel):
    generated_at: datetime
    hours: int
    bucket_seconds: int
    points: list[HostPointResponse]


class UsagePointResponse(BaseModel):
    start: datetime
    analyses: int
    tokens: int
    ok: int
    fallback: int
    error: int


class CallOutcomesResponse(BaseModel):
    attempts: int
    ok: int
    fallback: int
    error: int
    fallback_rate: float | None
    error_rate: float | None


class UsageSeriesResponse(BaseModel):
    generated_at: datetime
    hours: int
    bucket_hours: int
    points: list[UsagePointResponse]
    outcomes: CallOutcomesResponse
    by_hour: list[int]


class CollectorLogResponse(BaseModel):
    key: str
    log_file: str
    lines: list[str]
    last_run_at: datetime | None
    running: bool


class CollectorRunResponse(BaseModel):
    key: str
    started_at: datetime
