from dataclasses import replace
from datetime import datetime

from sqlalchemy import delete, func, or_, select, update

from apps.chat.adapter.outbound.orm_mappers.chat_message_orm_mapper import to_entity, to_orm
from apps.chat.adapter.outbound.orms.chat_message_orm import ChatAttachmentOrm, ChatMessageOrm
from apps.chat.app.ports.output.chat_message_port import ChatMessageRepositoryPort
from apps.chat.domain.entities.chat_message_entity import ChatMessage
from apps.chat.domain.value_objects.chat_room import DirectRoom, parse_room
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyChatMessageRepository(ChatMessageRepositoryPort):
    def add(self, message: ChatMessage, attachment: bytes | None = None) -> ChatMessage:
        with session_scope() as session:
            orm = to_orm(message)
            session.add(orm)
            session.flush()
            if attachment is not None:
                session.add(ChatAttachmentOrm(message_id=orm.id, content=attachment))
            return replace(message, id=orm.id)

    def attachment_content(self, message_id: int) -> bytes | None:
        with session_scope() as session:
            orm = session.get(ChatAttachmentOrm, message_id)
            return orm.content if orm else None

    def get(self, message_id: int) -> ChatMessage | None:
        with session_scope() as session:
            orm = session.get(ChatMessageOrm, message_id)
            return to_entity(orm) if orm else None

    def get_many(self, message_ids: list[int]) -> dict[int, ChatMessage]:
        if not message_ids:
            return {}
        with session_scope() as session:
            rows = session.execute(select(ChatMessageOrm).where(ChatMessageOrm.id.in_(message_ids))).scalars()
            return {orm.id: to_entity(orm) for orm in rows}

    def page(self, room: str, before_id: int | None, limit: int) -> list[ChatMessage]:
        query = select(ChatMessageOrm).where(ChatMessageOrm.room == room).order_by(ChatMessageOrm.id.desc()).limit(limit)
        if before_id is not None:
            query = query.where(ChatMessageOrm.id < before_id)
        with session_scope() as session:
            return [to_entity(orm) for orm in reversed(session.execute(query).scalars().all())]

    def after(self, rooms: list[str], after_id: int, limit: int) -> list[ChatMessage]:
        query = (
            select(ChatMessageOrm)
            .where(ChatMessageOrm.room.in_(rooms), ChatMessageOrm.id > after_id)
            .order_by(ChatMessageOrm.id)
            .limit(limit)
        )
        with session_scope() as session:
            return [to_entity(orm) for orm in session.execute(query).scalars()]

    def latest(self, room: str) -> ChatMessage | None:
        page = self.page(room, None, 1)
        return page[0] if page else None

    def latest_id(self) -> int:
        with session_scope() as session:
            return session.execute(select(func.coalesce(func.max(ChatMessageOrm.id), 0))).scalar_one()

    def count_by_sender_since(self, sender_id: int, since: datetime) -> int:
        query = select(func.count()).where(ChatMessageOrm.sender_id == sender_id, ChatMessageOrm.created_at >= since)
        with session_scope() as session:
            return session.execute(query).scalar_one()

    def count_unread(self, room: str, after_id: int, reader_id: int) -> int:
        query = select(func.count()).where(
            ChatMessageOrm.room == room,
            ChatMessageOrm.id > after_id,
            ChatMessageOrm.deleted_at.is_(None),
            or_(ChatMessageOrm.sender_id.is_(None), ChatMessageOrm.sender_id != reader_id),
        )
        with session_scope() as session:
            return session.execute(query).scalar_one()

    def direct_rooms_of(self, user_id: int) -> list[str]:
        query = select(ChatMessageOrm.room).distinct().where(
            or_(ChatMessageOrm.room.like(f"dm:{user_id}:%"), ChatMessageOrm.room.like(f"dm:%:{user_id}"))
        )
        with session_scope() as session:
            keys = session.execute(query).scalars().all()
        return [key for key in keys if _is_direct_room_of(key, user_id)]

    def mark_deleted(self, message_id: int, by: int, at: datetime) -> ChatMessage:
        with session_scope() as session:
            session.execute(
                update(ChatMessageOrm)
                .where(ChatMessageOrm.id == message_id, ChatMessageOrm.deleted_at.is_(None))
                .values(deleted_at=at, deleted_by=by)
            )
            return to_entity(session.get(ChatMessageOrm, message_id))

    def delete_rooms(self, rooms: list[str]) -> None:
        if not rooms:
            return
        with session_scope() as session:
            session.execute(delete(ChatMessageOrm).where(ChatMessageOrm.room.in_(rooms)))


def _is_direct_room_of(key: str, user_id: int) -> bool:
    try:
        room = parse_room(key)
    except ValueError:
        return False
    return isinstance(room, DirectRoom) and user_id in (room.low, room.high)
