from dataclasses import dataclass
from datetime import datetime


@dataclass
class AdminSession:
    """로그인 세션 — 쿠키에는 원문 토큰, DB에는 sha256 해시만 둔다 (DB 유출 시 세션 탈취 차단)."""

    token_hash: str
    admin_user_id: int
    created_at: datetime
    expires_at: datetime
    ip: str | None = None

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at
