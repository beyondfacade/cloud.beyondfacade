from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RulePolicy(StrEnum):
    ALLOW = "allow"  # 화이트리스트 — 자동 차단·로그인 제한에서 뺀다
    DENY = "deny"  # 블랙리스트 — 관리자 경로 접근을 막는다


class RuleTarget(StrEnum):
    IP = "ip"  # 단일 주소 또는 대역(CIDR)
    DEVICE = "device"  # 디바이스 쿠키 ID


@dataclass
class AccessRule:
    """화이트리스트·블랙리스트 한 줄 — IP 블랙리스트는 ip_block이 맡는다. expires_at이 없으면 무기한."""

    policy: RulePolicy
    target: RuleTarget
    value: str
    note: str
    created_at: datetime
    expires_at: datetime | None = None
    created_by: int | None = None
    id: int | None = None

    def is_active(self, now: datetime) -> bool:
        return self.expires_at is None or now < self.expires_at
