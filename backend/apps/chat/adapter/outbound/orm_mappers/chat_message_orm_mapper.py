"""Outbound Boundary Gate — entity ↔ ORM 변환."""

from apps.chat.adapter.outbound.orms.chat_message_orm import ChatMessageOrm
from apps.chat.domain.entities.chat_message_entity import ChatMessage

_FIELDS = (
    "room", "sender_id", "sender_username", "sender_role", "body", "created_at", "reply_to_id", "deleted_at",
    "deleted_by",
)


def to_orm(entity: ChatMessage) -> ChatMessageOrm:
    return ChatMessageOrm(**{name: getattr(entity, name) for name in _FIELDS})


def to_entity(orm: ChatMessageOrm) -> ChatMessage:
    return ChatMessage(id=orm.id, **{name: getattr(orm, name) for name in _FIELDS})
