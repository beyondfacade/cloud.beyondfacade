from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IpBlockDto:
    ip: str
    reason: str
    created_at: datetime
    expires_at: datetime | None
    created_by: str | None  # 차단한 관리자 username
