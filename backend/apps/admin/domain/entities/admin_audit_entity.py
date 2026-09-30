from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AuditAction(StrEnum):
    """관리자가 시스템을 바꾼 조치 — 보안 이벤트(access_event)와 달리 '누가 무엇을 했나'를 남긴다."""

    IP_BLOCK_CREATE = "ip_block.create"
    IP_BLOCK_DELETE = "ip_block.delete"
    IP_BLOCK_AUTO = "ip_block.auto"  # 자동 방어가 만든 차단 — 처리자는 "자동 방어"
    AUTO_DEFENSE_TOGGLE = "auto_defense.toggle"
    PROBE_RUN = "probe.run"
    COLLECTOR_RUN = "collector.run"
    # 화면에서 남의 계정 생성·등급·비밀번호를 바꾸던 조치 — 지금은 막혔지만 지난 기록을 읽고 거를 수 있게 남긴다
    USER_CREATE = "user.create"
    USER_ROLE = "user.role"
    USER_PASSWORD_RESET = "user.password_reset"
    USER_SUSPEND = "user.suspend"
    USER_REACTIVATE = "user.reactivate"
    USER_SESSIONS_REVOKE = "user.sessions_revoke"
    PASSWORD_CHANGE = "password.change"
    USERNAME_CHANGE = "username.change"


@dataclass
class AdminAudit:
    occurred_at: datetime
    action: AuditAction
    actor_username: str  # 계정이 지워져도 남도록 이름을 복사해 둔다
    target: str
    detail: str = ""
    ip: str | None = None
    actor_id: int | None = None
    id: int | None = None
