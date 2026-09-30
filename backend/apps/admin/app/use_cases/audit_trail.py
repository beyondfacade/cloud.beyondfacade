from datetime import datetime

from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.domain.entities.admin_audit_entity import AdminAudit, AuditAction


def audit_entry(
    now: datetime, actor: AdminPrincipalDto, action: AuditAction, target: str, detail: str = "", ip: str | None = None
) -> AdminAudit:
    return AdminAudit(
        occurred_at=now,
        action=action,
        actor_id=actor.id,
        actor_username=actor.username,
        target=target[:256],
        detail=detail[:512],
        ip=ip,
    )
