from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

import apps.admin.adapter.outbound.orms.admin_user_orm  # noqa: F401  FK 대상이 메타데이터에 있어야 한다
from core.matrix.grid_oracle_database_manager import OrmBase


class AdminSessionOrm(OrmBase):
    __tablename__ = "admin_session"

    token_hash: Mapped[str] = mapped_column(primary_key=True)  # sha256(쿠키 토큰)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("admin_user.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None]
