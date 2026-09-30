from datetime import datetime

from pydantic import BaseModel


class AccessEventResponse(BaseModel):
    id: int | None
    occurred_at: datetime
    kind: str
    ip: str | None
    method: str
    path: str
    status_code: int
    username: str | None
    device_id: str | None
    user_agent: str | None


class AccessEventPageResponse(BaseModel):
    items: list[AccessEventResponse]
    next_before_id: int | None


class SecurityAlertResponse(BaseModel):
    rule: str
    severity: str
    title: str
    ip: str | None
    count: int
    first_seen: datetime
    last_seen: datetime
    blocked: bool


class SecuritySummaryResponse(BaseModel):
    events_24h: int
    failed_logins_24h: int
    scanner_probes_24h: int
    server_errors_24h: int
    blocked_requests_24h: int
    open_alerts: int
    blocked_ips: int


class SecurityOverviewResponse(BaseModel):
    generated_at: datetime
    summary: SecuritySummaryResponse
    alerts: list[SecurityAlertResponse]
    recent_events: list[AccessEventResponse]
