from sqlalchemy import BigInteger, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionHousingAverageQuarterOrm(OrmBase):
    """아파트 평균 면적·시가 (OA-22163, 설계서 §4-3).

    `region_household_quarter`에 `value_float` 컬럼을 덧붙이지 않고 별도 테이블로 둔 근거:
    세대 수(개수)·평균 면적(㎡)·평균 시가(원)는 단위가 서로 다른 측정치다. 한 값 컬럼에 섞으면
    dim_type을 보지 않고는 SUM/AVG가 의미를 갖지 않는다.
    """

    __tablename__ = "region_housing_average_quarter"
    __table_args__ = (
        Index("ix_region_housing_average_quarter_region", "region_code", "year_quarter"),
    )

    adstrd_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    avg_area_m2: Mapped[float | None] = mapped_column(Float)
    avg_price: Mapped[int | None] = mapped_column(BigInteger)  # 원
