from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

import apps.admin.adapter.outbound.orms.admin_user_orm  # noqa: F401  FK 대상이 메타데이터에 있어야 한다
from core.matrix.grid_oracle_database_manager import OrmBase


class ChatReadOrm(OrmBase):
    """회원·방별로 어디까지 읽었는지 — 안 읽은 개수의 기준."""

    __tablename__ = "chat_read"

    user_id: Mapped[int] = mapped_column(ForeignKey("admin_user.id", ondelete="CASCADE"), primary_key=True)
    room: Mapped[str] = mapped_column(String(40), primary_key=True)
    last_read_id: Mapped[int] = mapped_column(BigInteger, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
