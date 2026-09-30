from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AccessEventKind(StrEnum):
    LOGIN_FAILED = "login_failed"
    LOGIN_SUCCEEDED = "login_succeeded"
    LOGIN_THROTTLED = "login_throttled"
    SIGNUP = "signup"
    SCANNER_PROBE = "scanner_probe"
    SERVER_ERROR = "server_error"
    BLOCKED_REQUEST = "blocked_request"


@dataclass
class AccessEvent:
    """보안 관점에서 남길 가치가 있는 요청 1건 — 전체 접근 로그가 아니다."""

    occurred_at: datetime
    kind: AccessEventKind
    ip: str | None
    method: str
    path: str
    status_code: int
    username: str | None = None  # 로그인 시도에 입력된 계정명 (없는 계정일 수 있다)
    admin_user_id: int | None = None
    id: int | None = None
