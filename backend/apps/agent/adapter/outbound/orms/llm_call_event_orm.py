"""llm_call_event ORM — LLM 호출 시도 1회당 한 행 (성공·폴백·오류)."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class LlmCallEventOrm(OrmBase):
    __tablename__ = "llm_call_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    model: Mapped[str]
    outcome: Mapped[str]  # ok | fallback | error
    error_kind: Mapped[str | None]
    latency_ms: Mapped[int]

    __table_args__ = (Index("ix_llm_call_event_occurred_at", "occurred_at"),)
