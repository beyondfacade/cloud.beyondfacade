from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

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


class AdminUserCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    role: RoleValue
    password: str = Field(min_length=1, max_length=512)  # 길이 규칙은 도메인이 판정해 WEAK_PASSWORD로 답한다


class AdminRoleRequest(BaseModel):
    role: RoleValue


class AdminStatusRequest(BaseModel):
    active: bool


class AdminPasswordResetRequest(BaseModel):
    password: str = Field(min_length=1, max_length=512)


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
