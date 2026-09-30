from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AdminUserDto:
    username: str
    role: str
    is_active: bool
    created_at: datetime | None
    last_login_at: datetime | None
    active_sessions: int


@dataclass(frozen=True)
class AdminSessionInfoDto:
    id: str  # token_hash 앞 12자 — 원본 해시는 내보내지 않는다
    created_at: datetime
    expires_at: datetime
    ip: str | None
    current: bool
