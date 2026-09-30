from collections.abc import Callable
from datetime import UTC, datetime

from apps.admin.app.dtos.housekeeping_dto import HousekeepingResultDto
from apps.admin.app.ports.input.housekeeping_use_case import HousekeepingUseCase
from apps.admin.app.ports.output.access_event_port import AccessEventRepositoryPort
from apps.admin.app.ports.output.admin_audit_port import AdminAuditRepositoryPort
from apps.admin.app.ports.output.admin_session_port import AdminSessionRepositoryPort
from apps.admin.app.ports.output.ip_block_port import IpBlockRepositoryPort
from apps.admin.domain.services.retention import ACCESS_EVENT_RETENTION, AUDIT_RETENTION


class HousekeepingInteractor(HousekeepingUseCase):
    def __init__(
        self,
        events: AccessEventRepositoryPort,
        audit: AdminAuditRepositoryPort,
        sessions: AdminSessionRepositoryPort,
        ip_blocks: IpBlockRepositoryPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._events = events
        self._audit = audit
        self._sessions = sessions
        self._ip_blocks = ip_blocks
        self._clock = clock

    def run(self) -> HousekeepingResultDto:
        now = self._clock()
        return HousekeepingResultDto(
            access_events=self._events.delete_before(now - ACCESS_EVENT_RETENTION),
            audit_entries=self._audit.delete_before(now - AUDIT_RETENTION),
            sessions=self._sessions.delete_expired(now),
            ip_blocks=self._ip_blocks.delete_expired(now),
        )
