from datetime import datetime

from pydantic import BaseModel


class AuditEntryResponse(BaseModel):
    id: int | None
    occurred_at: datetime
    action: str
    actor: str
    target: str
    detail: str
    ip: str | None


class AuditPageResponse(BaseModel):
    items: list[AuditEntryResponse]
    next_before_id: int | None
