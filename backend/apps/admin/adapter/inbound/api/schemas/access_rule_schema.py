from datetime import datetime

from pydantic import BaseModel, Field


class AccessRuleCreateRequest(BaseModel):
    policy: str = Field(max_length=16)  # allow | deny
    target: str = Field(max_length=16)  # ip | device
    value: str = Field(min_length=1, max_length=64)
    note: str = Field(default="", max_length=200)
    ttl_minutes: int | None = Field(default=None, ge=1, le=60 * 24 * 30)  # None = 무기한


class AccessRuleResponse(BaseModel):
    id: int
    policy: str
    target: str
    value: str
    note: str
    created_at: datetime
    expires_at: datetime | None
    created_by: str | None


class CurrentDeviceResponse(BaseModel):
    device_id: str | None
    user_agent: str | None
    allowed: bool
    denied: bool
