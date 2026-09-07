from datetime import date, datetime

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class FundingProgramOrm(OrmBase):
    """정책자금 공고 — 요약·메타데이터만 저장 (본문 전문 금지). 업종 M:N(funding_program_industry)은
    LLM 구조화 추출 후속 작업에서 추가."""

    __tablename__ = "funding_program"

    program_id: Mapped[str] = mapped_column(primary_key=True)  # 원천 공고 ID (bizinfo pblancId)
    source: Mapped[str]
    title: Mapped[str]
    org: Mapped[str]
    url: Mapped[str] = mapped_column(unique=True)
    apply_period: Mapped[str]
    exec_org: Mapped[str | None]
    field_category: Mapped[str | None]
    field_subcategory: Mapped[str | None]
    target_text: Mapped[str | None]
    hashtags: Mapped[str | None]
    apply_begin: Mapped[date | None]
    deadline: Mapped[date | None]
    summary: Mapped[str | None]
    posted_at: Mapped[datetime | None]
    source_updated_at: Mapped[datetime | None]
    is_expired: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        Index("ix_funding_program_open_deadline", "is_expired", "deadline"),  # 마감 임박순 조회
    )
