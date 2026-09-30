from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AccessRuleDto:
    id: int
    policy: str
    target: str
    value: str
    note: str
    created_at: datetime
    expires_at: datetime | None
    created_by: str | None  # 등록한 관리자 username


@dataclass(frozen=True)
class CurrentDeviceDto:
    device_id: str | None
    user_agent: str | None
    allowed: bool  # 화이트리스트(IP 또는 디바이스)에 걸리는지
    denied: bool  # 디바이스 블랙리스트에 있는지
