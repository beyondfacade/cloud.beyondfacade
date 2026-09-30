from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class AdminUserOrm(OrmBase):
    """회원 계정 — 공개 가입(비밀번호·구글)은 일반(viewer), 관리자(operator)는 인사팀·CLI로 올린다."""

    __tablename__ = "admin_user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str | None]  # 구글로만 가입한 계정은 NULL
    role: Mapped[str]  # viewer | operator
    is_active: Mapped[bool] = mapped_column(default=True)
    email: Mapped[str | None] = mapped_column(unique=True)  # 소문자
    google_sub: Mapped[str | None] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
