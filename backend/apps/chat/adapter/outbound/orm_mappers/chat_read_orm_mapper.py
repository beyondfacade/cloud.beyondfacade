"""Outbound Boundary Gate — entity ↔ ORM 변환."""

from apps.chat.adapter.outbound.orms.chat_read_orm import ChatReadOrm
from apps.chat.domain.entities.chat_read_entity import ChatRead

_FIELDS = ("user_id", "room", "last_read_id", "updated_at")


def to_orm(entity: ChatRead) -> ChatReadOrm:
    return ChatReadOrm(**{name: getattr(entity, name) for name in _FIELDS})


def to_entity(orm: ChatReadOrm) -> ChatRead:
    return ChatRead(**{name: getattr(orm, name) for name in _FIELDS})
