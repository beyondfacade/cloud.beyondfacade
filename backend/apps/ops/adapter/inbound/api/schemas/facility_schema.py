from datetime import datetime

from pydantic import BaseModel


class DiskResponse(BaseModel):
    mount: str
    total_bytes: int
    used_bytes: int
    free_bytes: int


class HostMetricsResponse(BaseModel):
    hostname: str
    platform: str
    cpu_count: int
    cpu_percent: float | None
    load_avg: list[float]
    memory_total_bytes: int | None
    memory_available_bytes: int | None
    swap_total_bytes: int | None
    swap_used_bytes: int | None
    uptime_seconds: int | None
    disks: list[DiskResponse]


class GpuResponse(BaseModel):
    index: int
    name: str
    memory_used_mb: int
    memory_total_mb: int
    utilization_percent: int
    temperature_c: int | None


class ServiceCheckResponse(BaseModel):
    name: str
    ok: bool
    latency_ms: int | None
    detail: str


class TableSizeResponse(BaseModel):
    name: str
    total_bytes: int
    row_estimate: int


class DatabaseStatusResponse(BaseModel):
    version: str
    size_bytes: int
    connections: int
    max_connections: int
    alembic_revision: str | None
    pgvector_version: str | None
    largest_tables: list[TableSizeResponse]


class CollectorStatusResponse(BaseModel):
    key: str
    label: str
    schedule: str
    status: str
    last_run_at: datetime | None
    table: str | None
    rows: int | None
    latest_data_at: datetime | None


class FacilitySnapshotResponse(BaseModel):
    generated_at: datetime
    host: HostMetricsResponse
    gpus: list[GpuResponse]
    services: list[ServiceCheckResponse]
    database: DatabaseStatusResponse | None
    collectors: list[CollectorStatusResponse]
