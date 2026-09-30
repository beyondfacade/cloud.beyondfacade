"""Outbound Boundary Gate — entity ↔ ORM 변환."""

from apps.admin.adapter.outbound.orms.admin_session_orm import AdminSessionOrm
from apps.admin.domain.entities.admin_session_entity import AdminSession

_FIELDS = ("token_hash", "admin_user_id", "created_at", "expires_at", "ip")


def to_orm(entity: AdminSession) -> AdminSessionOrm:
    return AdminSessionOrm(**{name: getattr(entity, name) for name in _FIELDS})


def to_entity(orm: AdminSessionOrm) -> AdminSession:
    return AdminSession(**{name: getattr(orm, name) for name in _FIELDS})
