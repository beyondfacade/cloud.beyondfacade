"""Outbound Boundary Gate — entity ↔ ORM 변환."""

from apps.admin.adapter.outbound.orms.access_event_orm import AccessEventOrm
from apps.admin.domain.entities.access_event_entity import AccessEvent, AccessEventKind

_FIELDS = ("occurred_at", "ip", "method", "path", "status_code", "username", "admin_user_id", "device_id", "user_agent")


def to_orm(entity: AccessEvent) -> AccessEventOrm:
    return AccessEventOrm(kind=entity.kind.value, **{name: getattr(entity, name) for name in _FIELDS})


def to_entity(orm: AccessEventOrm) -> AccessEvent:
    return AccessEvent(id=orm.id, kind=AccessEventKind(orm.kind), **{name: getattr(orm, name) for name in _FIELDS})
