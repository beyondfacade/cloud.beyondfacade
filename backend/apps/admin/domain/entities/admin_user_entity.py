from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AdminRole(StrEnum):
    """일반(viewer)은 관리자 페이지 읽기까지, 관리자(operator)는 차단·프로브·계정 변경 같은 쓰기까지."""

    VIEWER = "viewer"
    OPERATOR = "operator"

    @property
    def can_operate(self) -> bool:
        return self is AdminRole.OPERATOR


@dataclass
class AdminUser:
    username: str
    password_hash: str | None  # scrypt 인코딩 문자열 — 원문은 어디에도 남기지 않는다. 구글 전용 계정은 None
    role: AdminRole
    is_active: bool = True
    email: str | None = None
    google_sub: str | None = None
    id: int | None = None
    created_at: datetime | None = None
    last_login_at: datetime | None = None
