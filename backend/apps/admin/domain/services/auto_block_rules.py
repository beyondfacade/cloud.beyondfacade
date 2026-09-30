"""자동 차단 규칙 — 같은 IP의 로그인 실패·스캐너 탐색이 창 안에서 임계치에 닿으면 그 IP를 기한부로 막는다.

알림 규칙(alert_rules)은 보여 주기만 하고, 이 규칙은 실제로 ip_block을 만든다.
한 번 자동 차단됐던 IP가 풀린 뒤 다시 걸리면 더 길게 막는다.
"""

import ipaddress
from dataclasses import dataclass
from datetime import timedelta

from apps.admin.domain.entities.access_event_entity import AccessEventKind
from apps.admin.domain.entities.ip_block_entity import IpBlock

AUTO_BLOCK_ACTOR = "자동 방어"
AUTO_BLOCK_REASON_PREFIX = "자동 차단"
_AUTH_FAILURE_STATUSES = frozenset({401, 429})
_PROTECTED_PREFIX = "/admin"


@dataclass(frozen=True)
class AutoBlockRule:
    rule: str
    title: str
    kinds: tuple[AccessEventKind, ...]
    window: timedelta
    threshold: int
    block: timedelta
    repeat_block: timedelta

    def reason(self, count: int, repeat: bool) -> str:
        again = " · 재차단" if repeat else ""
        return f"{AUTO_BLOCK_REASON_PREFIX} · {self.title} {count}회{again}"


AUTO_BLOCK_RULES: tuple[AutoBlockRule, ...] = (
    AutoBlockRule(
        rule="brute_force_login",
        title="로그인 실패",
        kinds=(AccessEventKind.LOGIN_FAILED, AccessEventKind.LOGIN_THROTTLED),
        window=timedelta(minutes=15),
        threshold=10,
        block=timedelta(hours=1),
        repeat_block=timedelta(hours=24),
    ),
    AutoBlockRule(
        rule="scanner_probe",
        title="취약점 스캐너 경로 탐색",
        kinds=(AccessEventKind.SCANNER_PROBE,),
        window=timedelta(hours=1),
        threshold=5,
        block=timedelta(hours=24),
        repeat_block=timedelta(days=7),
    ),
)


def auto_block_exempt(ip: str | None) -> bool:
    """루프백은 같은 서버의 프록시·운영자 자신이라 막지 않는다. 형식이 틀린 값도 막을 대상이 아니다."""
    if ip is None:
        return True
    try:
        return ipaddress.ip_address(ip).is_loopback
    except ValueError:
        return True


def triggers_auto_block(kind: AccessEventKind | None, method: str, path: str, status: int) -> bool:
    """로그인·가입 실패(관리자 경로 POST의 401·429)와 스캐너 탐색 응답만 검사한다.
    비로그인 방문자의 세션 확인(GET 401)까지 검사하면 매 페이지마다 DB를 읽게 된다."""
    if kind is AccessEventKind.SCANNER_PROBE:
        return True
    return method == "POST" and path.startswith(_PROTECTED_PREFIX) and status in _AUTH_FAILURE_STATUSES


def is_auto_block(block: IpBlock) -> bool:
    return block.created_by is None and block.reason.startswith(AUTO_BLOCK_REASON_PREFIX)
