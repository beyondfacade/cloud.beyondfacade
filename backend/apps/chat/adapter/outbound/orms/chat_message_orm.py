from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

import apps.admin.adapter.outbound.orms.admin_user_orm  # noqa: F401  FK 대상이 메타데이터에 있어야 한다
from core.matrix.grid_oracle_database_manager import OrmBase


class ChatMessageOrm(OrmBase):
    """글로벌 채팅 메시지 — 보낸 사람 이름·등급은 보낸 때 그대로 남긴다 (실시간 알림이 DB를 다시 읽지 않게)."""

    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    room: Mapped[str] = mapped_column(String(40))
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("admin_user.id", ondelete="SET NULL"))
    sender_username: Mapped[str]
    sender_role: Mapped[str]
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reply_to_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("chat_message.id", ondelete="SET NULL"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[int | None] = mapped_column(ForeignKey("admin_user.id", ondelete="SET NULL"))

    __table_args__ = (
        Index("ix_chat_message_room_id", "room", "id"),
        Index("ix_chat_message_sender_created_at", "sender_id", "created_at"),
    )
