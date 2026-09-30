from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

import apps.admin.adapter.outbound.orms.admin_user_orm  # noqa: F401  FK 대상이 메타데이터에 있어야 한다
from core.matrix.grid_oracle_database_manager import OrmBase


class AccessEventOrm(OrmBase):
    """보안 이벤트 — 로그인 시도·스캐너 탐색·5xx·차단 요청만 남긴다 (전체 접근 로그 아님)."""

    __tablename__ = "access_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str]
    ip: Mapped[str | None]
    method: Mapped[str]
    path: Mapped[str]
    status_code: Mapped[int]
    username: Mapped[str | None]
    admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_user.id", ondelete="SET NULL"))
    device_id: Mapped[str | None]
    user_agent: Mapped[str | None]

    __table_args__ = (
        Index("ix_access_event_occurred_at", "occurred_at"),
        Index("ix_access_event_kind_ip_time", "kind", "ip", "occurred_at"),  # 로그인 스로틀 카운트
    )
