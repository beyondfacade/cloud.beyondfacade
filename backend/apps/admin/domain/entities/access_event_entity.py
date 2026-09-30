from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from apps.admin.domain.entities.client_entity import Client


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
    device_id: str | None = None
    user_agent: str | None = None
    id: int | None = None


def client_event(
    now: datetime,
    kind: AccessEventKind,
    client: Client,
    method: str,
    path: str,
    status_code: int,
    username: str | None = None,
    admin_user_id: int | None = None,
) -> AccessEvent:
    return AccessEvent(
        occurred_at=now,
        kind=kind,
        ip=client.ip,
        method=method,
        path=path[:512],
        status_code=status_code,
        username=username[:64] if username is not None else None,
        admin_user_id=admin_user_id,
        device_id=client.device_id,
        user_agent=client.user_agent[:300] if client.user_agent else None,
    )
