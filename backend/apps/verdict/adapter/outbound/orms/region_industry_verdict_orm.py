from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.industry_orm  # noqa: F401
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionIndustryVerdictOrm(OrmBase):
    """행정동×업종 판정 1행 — 새벽 배치 재생성 (설계서 §4-3).
    signals_json은 카드가 통째로 읽고 질의 축이 아니라 열로 풀지 않는다(명시적 역정규화)."""

    __tablename__ = "region_industry_verdict"
    __table_args__ = (
        # 단계구분도 조회(GET /verdicts?industry=)가 업종으로 전 행정동을 훑는다
        Index("ix_region_industry_verdict_industry", "industry_id"),
    )

    region_code: Mapped[str] = mapped_column(ForeignKey("region.region_code"), primary_key=True)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industry.industry_id"), primary_key=True)
    verdict_code: Mapped[str] = mapped_column(String(12))  # red | orange | clear | insufficient
    strong_count: Mapped[int] = mapped_column(SmallInteger)
    on_count: Mapped[int] = mapped_column(SmallInteger)
    signals_json: Mapped[str] = mapped_column(Text)  # 프로필의 신호 JSON 배열
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    basis: Mapped[str] = mapped_column(String(12), server_default="permit")  # permit | proxy | aggregate (설계서 §9)
