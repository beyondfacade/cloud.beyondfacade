from datetime import date, datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.district_orm  # noqa: F401
import apps.master.adapter.outbound.orms.industry_orm  # noqa: F401
import apps.master.adapter.outbound.orms.industry_subcategory_orm  # noqa: F401
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class StoreOrm(OrmBase):
    """점포 (인허가 단위) — 좌표는 EPSG:5174→WGS84 변환값 (2026-08-25 브이월드 교차검증)."""

    __tablename__ = "store"
    __table_args__ = (
        Index("ix_store_industry_district_updated", "industry_id", "district_code", "source_updated_at"),
    )

    store_id: Mapped[str] = mapped_column(primary_key=True)  # 인허가 관리번호(MNG_NO)
    name: Mapped[str]
    industry_id: Mapped[str] = mapped_column(ForeignKey("industry.industry_id"))
    district_code: Mapped[str] = mapped_column(ForeignKey("district.district_code"))
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    subcategory_id: Mapped[str | None] = mapped_column(
        ForeignKey("industry_subcategory.subcategory_id")
    )
    open_date: Mapped[date | None]
    close_date: Mapped[date | None]
    status_code: Mapped[str]
    status_name: Mapped[str]
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    source_updated_at: Mapped[datetime]
