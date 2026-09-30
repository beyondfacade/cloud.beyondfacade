from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

import apps.admin.adapter.outbound.orms.admin_user_orm  # noqa: F401  FK 대상이 메타데이터에 있어야 한다
from core.matrix.grid_oracle_database_manager import OrmBase


class AdminAuditOrm(OrmBase):
    """관리자 조치 감사 로그 — IP 차단·계정 변경·수동 실행처럼 시스템을 바꾼 일만 남긴다."""

    __tablename__ = "admin_audit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("admin_user.id", ondelete="SET NULL"))
    actor_username: Mapped[str]
    action: Mapped[str]
    target: Mapped[str]
    detail: Mapped[str] = mapped_column(default="")
    ip: Mapped[str | None]

    __table_args__ = (
        Index("ix_admin_audit_occurred_at", "occurred_at"),
        Index("ix_admin_audit_action_id", "action", "id"),
    )
