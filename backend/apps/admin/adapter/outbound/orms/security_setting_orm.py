from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

import apps.admin.adapter.outbound.orms.admin_user_orm  # noqa: F401  FK 대상이 메타데이터에 있어야 한다
from core.matrix.grid_oracle_database_manager import OrmBase


class SecuritySettingOrm(OrmBase):
    """보안 동작 스위치 — 행이 없으면 엔티티 기본값을 쓴다."""

    __tablename__ = "security_setting"

    key: Mapped[str] = mapped_column(primary_key=True)
    enabled: Mapped[bool]
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("admin_user.id", ondelete="SET NULL"))
