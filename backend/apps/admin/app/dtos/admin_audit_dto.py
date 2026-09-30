from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class AuditEntryDto:
    id: int | None
    occurred_at: datetime
    action: str
    actor: str
    target: str
    detail: str
    ip: str | None


@dataclass(frozen=True)
class AuditPageDto:
    items: list[AuditEntryDto] = field(default_factory=list)
    next_before_id: int | None = None  # None이면 마지막 쪽
