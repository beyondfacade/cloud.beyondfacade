from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class AccessEventDto:
    id: int | None
    occurred_at: datetime
    kind: str
    ip: str | None
    method: str
    path: str
    status_code: int
    username: str | None


@dataclass(frozen=True)
class AccessEventPageDto:
    items: list[AccessEventDto] = field(default_factory=list)
    next_before_id: int | None = None  # None이면 마지막 쪽


@dataclass(frozen=True)
class SecurityAlertDto:
    rule: str
    severity: str
    title: str
    ip: str | None
    count: int
    first_seen: datetime
    last_seen: datetime
    blocked: bool


@dataclass(frozen=True)
class SecuritySummaryDto:
    events_24h: int = 0
    failed_logins_24h: int = 0
    scanner_probes_24h: int = 0
    server_errors_24h: int = 0
    blocked_requests_24h: int = 0
    open_alerts: int = 0
    blocked_ips: int = 0


@dataclass(frozen=True)
class SecurityOverviewDto:
    generated_at: datetime
    summary: SecuritySummaryDto
    alerts: list[SecurityAlertDto] = field(default_factory=list)
    recent_events: list[AccessEventDto] = field(default_factory=list)
