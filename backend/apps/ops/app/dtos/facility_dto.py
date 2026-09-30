from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class DiskDto:
    mount: str
    total_bytes: int
    used_bytes: int
    free_bytes: int


@dataclass(frozen=True)
class HostMetricsDto:
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
    disks: list[DiskDto] = field(default_factory=list)


@dataclass(frozen=True)
class GpuDto:
    index: int
    name: str
    memory_used_mb: int
    memory_total_mb: int
    utilization_percent: int
    temperature_c: int | None


@dataclass(frozen=True)
class ServiceCheckDto:
    name: str
    ok: bool
    latency_ms: int | None
    detail: str


@dataclass(frozen=True)
class TableSizeDto:
    name: str
    total_bytes: int
    row_estimate: int


@dataclass(frozen=True)
class DatabaseStatusDto:
    version: str
    size_bytes: int
    connections: int
    max_connections: int
    alembic_revision: str | None
    pgvector_version: str | None
    largest_tables: list[TableSizeDto] = field(default_factory=list)


@dataclass(frozen=True)
class CollectorStatusDto:
    key: str
    label: str
    schedule: str
    status: str  # ok | late | missing
    last_run_at: datetime | None
    table: str | None
    rows: int | None
    latest_data_at: datetime | None


@dataclass(frozen=True)
class FacilitySnapshotDto:
    generated_at: datetime
    host: HostMetricsDto
    gpus: list[GpuDto]
    services: list[ServiceCheckDto]
    database: DatabaseStatusDto | None
    collectors: list[CollectorStatusDto]
