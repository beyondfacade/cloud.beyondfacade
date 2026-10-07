"""analysis_pending ORM — POST /analysis와 SSE 사이의 대기 분석 장부 (워커 간 공유)."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.industry_orm  # noqa: F401
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase

FK_REGION = "fk_analysis_pending_region"
FK_INDUSTRY = "fk_analysis_pending_industry"


class AnalysisPendingOrm(OrmBase):
    __tablename__ = "analysis_pending"
    # 만료 판정·정리가 created_at으로 훑는다
    __table_args__ = (Index("ix_analysis_pending_created_at", "created_at"),)

    analysis_id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid4 hex
    region_code: Mapped[str] = mapped_column(ForeignKey("region.region_code", name=FK_REGION))
    industry_id: Mapped[str] = mapped_column(ForeignKey("industry.industry_id", name=FK_INDUSTRY))
    question: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str]
    budget: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
