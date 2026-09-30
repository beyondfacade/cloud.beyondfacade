from collections.abc import Callable
from datetime import UTC, datetime

from apps.admin.app.dtos.admin_audit_dto import AuditEntryDto, AuditPageDto
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.app.ports.input.admin_audit_use_case import AdminAuditUseCase
from apps.admin.app.ports.output.admin_audit_port import AdminAuditRepositoryPort
from apps.admin.app.use_cases.audit_trail import audit_entry
from apps.admin.domain.entities.admin_audit_entity import AdminAudit, AuditAction


def _to_dto(entry: AdminAudit) -> AuditEntryDto:
    return AuditEntryDto(
        id=entry.id,
        occurred_at=entry.occurred_at,
        action=entry.action.value,
        actor=entry.actor_username,
        target=entry.target,
        detail=entry.detail,
        ip=entry.ip,
    )


class AdminAuditInteractor(AdminAuditUseCase):
    def __init__(
        self, audit: AdminAuditRepositoryPort, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._audit = audit
        self._clock = clock

    def myself(self) -> AuditPageDto:
        return AuditPageDto(
            items=[
                AuditEntryDto(
                    id=0, occurred_at=datetime(2026, 9, 30, tzinfo=UTC), action=AuditAction.PROBE_RUN.value,
                    actor="myself", target="admin_audit 배선 검증", detail="", ip=None,
                )
            ]
        )

    def record(
        self, actor: AdminPrincipalDto, action: AuditAction, target: str, detail: str = "", ip: str | None = None
    ) -> None:
        self._audit.add(audit_entry(self._clock(), actor, action, target, detail, ip))

    def page(self, action: AuditAction | None, before_id: int | None, limit: int) -> AuditPageDto:
        rows = self._audit.page(action, before_id, limit + 1)  # 한 건 더 읽어 다음 쪽 유무를 안다
        items = [_to_dto(entry) for entry in rows[:limit]]
        return AuditPageDto(items=items, next_before_id=items[-1].id if len(rows) > limit else None)
