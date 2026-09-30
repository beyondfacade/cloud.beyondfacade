from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

import apps.admin.adapter.outbound.orms.admin_user_orm  # noqa: F401  FK 대상이 메타데이터에 있어야 한다
from core.matrix.grid_oracle_database_manager import OrmBase


class AccessRuleOrm(OrmBase):
    """화이트리스트(allow)·블랙리스트(deny) — IP 블랙리스트는 ip_block 테이블."""

    __tablename__ = "access_rule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    policy: Mapped[str]
    target: Mapped[str]
    value: Mapped[str]
    note: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # None = 무기한
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admin_user.id", ondelete="SET NULL"))

    __table_args__ = (UniqueConstraint("policy", "target", "value", name="uq_access_rule_policy_target_value"),)
