from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AdminPrincipalDto:
    id: int
    username: str
    role: str
    can_operate: bool
    hourly_rate: int | None = None  # 전문가 상담 시간당 요금(원)
    specialty: str | None = None  # 전문가 전문 업종
    avatar_version: int | None = None  # 프로필 사진 버전 — 없으면 None


@dataclass(frozen=True)
class LoginResultDto:
    token: str  # 쿠키로만 내보낸다 — 응답 본문에 싣지 않는다
    expires_at: datetime
    principal: AdminPrincipalDto


@dataclass(frozen=True)
class GoogleLoginStartDto:
    url: str
    state: str  # 콜백에서 대조할 값 — 브라우저 쿠키에만 둔다
    code_verifier: str
