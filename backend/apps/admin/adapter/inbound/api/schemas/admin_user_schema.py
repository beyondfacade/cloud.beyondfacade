from datetime import datetime
from typing import Literal

from pydantic import BaseModel

RoleValue = Literal["viewer", "operator"]


class AdminUserResponse(BaseModel):
    username: str
    role: str
    is_active: bool
    created_at: datetime | None
    last_login_at: datetime | None
    active_sessions: int
    email: str | None
    has_password: bool
    has_google: bool


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]


class AdminStatusRequest(BaseModel):
    active: bool


class AdminSessionInfoResponse(BaseModel):
    id: str
    created_at: datetime
    expires_at: datetime
    ip: str | None
    current: bool


class AdminSessionListResponse(BaseModel):
    items: list[AdminSessionInfoResponse]


class RevokedSessionsResponse(BaseModel):
    revoked: int
