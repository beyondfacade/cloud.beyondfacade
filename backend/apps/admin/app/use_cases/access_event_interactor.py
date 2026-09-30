from collections import Counter
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from apps.admin.app.dtos.access_event_dto import (
    AccessEventDto,
    AccessEventPageDto,
    SecurityAlertDto,
    SecurityOverviewDto,
    SecuritySummaryDto,
)
from apps.admin.app.ports.input.access_event_use_case import AccessEventUseCase
from apps.admin.app.ports.output.access_event_port import AccessEventRepositoryPort
from apps.admin.app.ports.output.ip_block_port import IpBlockRepositoryPort
from apps.admin.domain.entities.access_event_entity import AccessEvent, AccessEventKind
from apps.admin.domain.services.alert_rules import evaluate_alerts

_OVERVIEW_WINDOW = timedelta(hours=24)
_OVERVIEW_EVENT_CAP = 5000  # 공격 폭주 시에도 개요 계산이 무한정 커지지 않게
_RECENT_EVENTS = 50


def _to_event_dto(event: AccessEvent) -> AccessEventDto:
    return AccessEventDto(
        id=event.id,
        occurred_at=event.occurred_at,
        kind=event.kind.value,
        ip=event.ip,
        method=event.method,
        path=event.path,
        status_code=event.status_code,
        username=event.username,
    )


class AccessEventInteractor(AccessEventUseCase):
    def __init__(
        self,
        events: AccessEventRepositoryPort,
        ip_blocks: IpBlockRepositoryPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._events = events
        self._ip_blocks = ip_blocks
        self._clock = clock

    def myself(self) -> SecurityOverviewDto:
        return SecurityOverviewDto(generated_at=datetime(2026, 9, 29, tzinfo=UTC), summary=SecuritySummaryDto())

    def record(self, kind: AccessEventKind, ip: str | None, method: str, path: str, status_code: int) -> None:
        self._events.add(
            AccessEvent(
                occurred_at=self._clock(), kind=kind, ip=ip, method=method, path=path[:512], status_code=status_code
            )
        )

    def overview(self) -> SecurityOverviewDto:
        now = self._clock()
        events = self._events.list_since(now - _OVERVIEW_WINDOW, _OVERVIEW_EVENT_CAP)
        blocked_ips = {block.ip for block in self._ip_blocks.list_active(now)}
        alerts = evaluate_alerts(events, blocked_ips, now)
        kinds = Counter(event.kind for event in events)
        return SecurityOverviewDto(
            generated_at=now,
            summary=SecuritySummaryDto(
                events_24h=len(events),
                failed_logins_24h=kinds[AccessEventKind.LOGIN_FAILED],
                scanner_probes_24h=kinds[AccessEventKind.SCANNER_PROBE],
                server_errors_24h=kinds[AccessEventKind.SERVER_ERROR],
                blocked_requests_24h=kinds[AccessEventKind.BLOCKED_REQUEST],
                open_alerts=len(alerts),
                blocked_ips=len(blocked_ips),
            ),
            alerts=[SecurityAlertDto(**asdict(alert)) for alert in alerts],
            recent_events=[_to_event_dto(event) for event in events[:_RECENT_EVENTS]],
        )

    def events(
        self, kind: AccessEventKind | None, ip: str | None, hours: int, before_id: int | None, limit: int
    ) -> AccessEventPageDto:
        since = self._clock() - timedelta(hours=hours)
        rows = self._events.search(kind, ip, since, before_id, limit + 1)  # 한 건 더 읽어 다음 쪽 유무를 안다
        items = [_to_event_dto(event) for event in rows[:limit]]
        return AccessEventPageDto(items=items, next_before_id=items[-1].id if len(rows) > limit else None)
