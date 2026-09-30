from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AdminRole(StrEnum):
    """조회 관리자(viewer)는 보기만, 운영 관리자(operator)는 차단·프로브 같은 변경까지."""

    VIEWER = "viewer"
    OPERATOR = "operator"

    @property
    def can_operate(self) -> bool:
        return self is AdminRole.OPERATOR


@dataclass
class AdminUser:
    username: str
    password_hash: str  # scrypt 인코딩 문자열 — 원문은 어디에도 남기지 않는다
    role: AdminRole
    is_active: bool = True
    id: int | None = None
    created_at: datetime | None = None
    last_login_at: datetime | None = None
