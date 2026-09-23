"""analysis_report ORM — 에이전트 분석 리포트 영속화."""

from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class AnalysisReportOrm(OrmBase):
    __tablename__ = "analysis_report"

    id: Mapped[str] = mapped_column(primary_key=True)  # = analysis_id (POST uuid)
    region_code: Mapped[str]
    industry: Mapped[str]
    question: Mapped[str | None]
    report_md: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[str] = mapped_column(Text)
    model: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
