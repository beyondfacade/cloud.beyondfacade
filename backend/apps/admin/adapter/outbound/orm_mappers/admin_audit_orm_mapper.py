"""Outbound Boundary Gate — entity ↔ ORM 변환."""

from apps.admin.adapter.outbound.orms.admin_audit_orm import AdminAuditOrm
from apps.admin.domain.entities.admin_audit_entity import AdminAudit, AuditAction

_FIELDS = ("occurred_at", "actor_id", "actor_username", "target", "detail", "ip")


def to_orm(entity: AdminAudit) -> AdminAuditOrm:
    return AdminAuditOrm(action=entity.action.value, **{name: getattr(entity, name) for name in _FIELDS})


def to_entity(orm: AdminAuditOrm) -> AdminAudit:
    return AdminAudit(id=orm.id, action=AuditAction(orm.action), **{name: getattr(orm, name) for name in _FIELDS})
