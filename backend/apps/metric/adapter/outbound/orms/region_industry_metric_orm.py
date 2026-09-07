from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.industry_orm  # noqa: F401
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionIndustryMetricOrm(OrmBase):
    """행정동×업종×연도 집계 지표 — store 원천에서 배치 재생성 (역정규화 허용 계층, docs/erd.md)."""

    __tablename__ = "region_industry_metric"
    __table_args__ = (
        # 단계구분도 조회(GET /metrics)가 업종×연도로 전 행정동을 훑는다
        Index("ix_region_industry_metric_industry_year", "industry_id", "year"),
    )

    region_code: Mapped[str] = mapped_column(
        ForeignKey("region.region_code"), primary_key=True
    )
    industry_id: Mapped[str] = mapped_column(
        ForeignKey("industry.industry_id"), primary_key=True
    )
    year: Mapped[int] = mapped_column(primary_key=True)
    store_count: Mapped[int]  # 해당 연도 말(12-31) 기준 영업 중 점포 수
    open_count: Mapped[int]  # 당해 개업 수
    close_count: Mapped[int]  # 당해 폐업 수
    closure_rate: Mapped[float | None]  # close_count ÷ 전년 말 store_count
    growth_rate: Mapped[float | None]  # (open_count − close_count) ÷ 전년 말 store_count
