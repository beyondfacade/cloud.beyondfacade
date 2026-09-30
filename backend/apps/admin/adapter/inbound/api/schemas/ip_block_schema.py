from datetime import datetime

from pydantic import BaseModel, Field


class IpBlockCreateRequest(BaseModel):
    ip: str = Field(min_length=1, max_length=64)
    reason: str = Field(default="", max_length=200)
    ttl_minutes: int | None = Field(default=None, ge=1, le=60 * 24 * 30)  # None = 무기한


class IpBlockResponse(BaseModel):
    ip: str
    reason: str
    created_at: datetime
    expires_at: datetime | None
    created_by: str | None
