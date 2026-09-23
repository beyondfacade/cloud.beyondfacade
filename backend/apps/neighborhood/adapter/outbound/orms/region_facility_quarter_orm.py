from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionFacilityQuarterOrm(OrmBase):
    """집객시설 — 1NF long (OA-22169, 설계서 §4-4). 원본 1행 → total + 19종 = 20행.

    시설 종류가 늘어도 DDL이 필요 없다. 원천 공란이 흔한데 "시설이 0개"와 "집계되지 않음"을
    구분해야 하므로 0으로 채우지 않고 NULL로 둔다.
    """

    __tablename__ = "region_facility_quarter"
    __table_args__ = (
        Index("ix_region_facility_quarter_region", "region_code", "year_quarter", "facility_type"),
    )

    adstrd_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)
    # 최장 elementary_school
    facility_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    facility_count: Mapped[int | None] = mapped_column(Integer)
