from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AdminPrincipalDto:
    id: int
    username: str
    role: str
    can_operate: bool


@dataclass(frozen=True)
class LoginResultDto:
    token: str  # 쿠키로만 내보낸다 — 응답 본문에 싣지 않는다
    expires_at: datetime
    principal: AdminPrincipalDto
