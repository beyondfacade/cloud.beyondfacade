from dataclasses import dataclass
from datetime import datetime


@dataclass
class IpBlock:
    """관리자 경로(/admin/*) 접근 차단 — expires_at이 없으면 무기한."""

    ip: str
    reason: str
    created_at: datetime
    expires_at: datetime | None = None
    created_by: int | None = None

    def is_active(self, now: datetime) -> bool:
        return self.expires_at is None or now < self.expires_at
