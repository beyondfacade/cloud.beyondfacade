from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

import apps.admin.adapter.outbound.orms.admin_user_orm  # noqa: F401  FK 대상이 메타데이터에 있어야 한다
from core.matrix.grid_oracle_database_manager import OrmBase


class IpBlockOrm(OrmBase):
    __tablename__ = "ip_block"

    ip: Mapped[str] = mapped_column(primary_key=True)
    reason: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # None = 무기한
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admin_user.id", ondelete="SET NULL"))
