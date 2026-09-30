"""보안 알림 규칙 — 최근 보안 이벤트에서 알림을 계산한다 (저장하지 않는 파생 값).

규칙마다 창·임계치·심각도가 다르다. 규칙 추가는 `_RULES`에 클래스 하나를 더하는 것으로 끝난다
(CLAUDE.md §5 Strategy).
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from apps.admin.domain.entities.access_event_entity import AccessEvent, AccessEventKind

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass(frozen=True)
class SecurityAlert:
    rule: str
    severity: str
    title: str
    ip: str | None
    count: int
    first_seen: datetime
    last_seen: datetime
    blocked: bool


class AlertRule(ABC):
    rule: str
    kind: AccessEventKind
    window: timedelta

    @abstractmethod
    def severity(self, count: int) -> str | None:
        """건수에 따른 심각도 — 임계치 미만이면 None."""

    @abstractmethod
    def title(self, ip: str | None, count: int) -> str: ...

    def group_key(self, event: AccessEvent) -> str | None:
        return event.ip

    def evaluate(self, events: list[AccessEvent], blocked_ips: set[str], now: datetime) -> list[SecurityAlert]:
        groups: dict[str | None, list[AccessEvent]] = defaultdict(list)
        for event in events:
            if event.kind == self.kind and now - event.occurred_at <= self.window:
                groups[self.group_key(event)].append(event)
        alerts = []
        for ip, grouped in groups.items():
            severity = self.severity(len(grouped))
            if severity is None:
                continue
            times = [e.occurred_at for e in grouped]
            alerts.append(
                SecurityAlert(
                    rule=self.rule,
                    severity=severity,
                    title=self.title(ip, len(grouped)),
                    ip=ip,
                    count=len(grouped),
                    first_seen=min(times),
                    last_seen=max(times),
                    blocked=ip in blocked_ips,
                )
            )
        return alerts


class BruteForceLoginRule(AlertRule):
    rule = "brute_force_login"
    kind = AccessEventKind.LOGIN_FAILED
    window = timedelta(minutes=15)

    def severity(self, count: int) -> str | None:
        return "critical" if count >= 10 else "high" if count >= 5 else None

    def title(self, ip: str | None, count: int) -> str:
        return f"관리자 로그인 실패 {count}회 (15분)"


class ScannerProbeRule(AlertRule):
    rule = "scanner_probe"
    kind = AccessEventKind.SCANNER_PROBE
    window = timedelta(hours=1)

    def severity(self, count: int) -> str | None:
        return "medium" if count >= 3 else None

    def title(self, ip: str | None, count: int) -> str:
        return f"취약점 스캐너 경로 탐색 {count}회 (1시간)"


class ServerErrorBurstRule(AlertRule):
    rule = "server_error_burst"
    kind = AccessEventKind.SERVER_ERROR
    window = timedelta(minutes=15)

    def group_key(self, event: AccessEvent) -> str | None:
        return None  # 장애는 IP가 아니라 서비스 단위로 본다

    def severity(self, count: int) -> str | None:
        return "high" if count >= 5 else None

    def title(self, ip: str | None, count: int) -> str:
        return f"서버 오류(5xx) {count}건 (15분)"


class BlockedRetryRule(AlertRule):
    rule = "blocked_retry"
    kind = AccessEventKind.BLOCKED_REQUEST
    window = timedelta(hours=1)

    def severity(self, count: int) -> str | None:
        return "low" if count >= 5 else None

    def title(self, ip: str | None, count: int) -> str:
        return f"차단된 IP의 재접근 {count}회 (1시간)"


_RULES: tuple[AlertRule, ...] = (
    BruteForceLoginRule(),
    ScannerProbeRule(),
    ServerErrorBurstRule(),
    BlockedRetryRule(),
)


def evaluate_alerts(events: list[AccessEvent], blocked_ips: set[str], now: datetime) -> list[SecurityAlert]:
    alerts = [alert for rule in _RULES for alert in rule.evaluate(events, blocked_ips, now)]
    return sorted(alerts, key=lambda a: (_SEVERITY_ORDER[a.severity], -a.count))
