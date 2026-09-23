from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionHouseholdQuarterOrm(OrmBase):
    """가구·아파트 스톡 — 1NF long (OA-22183 가구 3종 + OA-22163, 설계서 §4-3).

    상주인구 원천의 가구 3종과 아파트 데이터셋을 합친다 — 둘 다 주거 스톡이고 세대/단지 개수라
    단위가 같다. 단위가 다른 평균 면적·시가는 `region_housing_average_quarter`로 뺐다.
    """

    __tablename__ = "region_household_quarter"
    __table_args__ = (
        Index(
            "ix_region_household_quarter_region",
            "region_code",
            "year_quarter",
            "dim_type",
        ),
    )

    adstrd_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)
    dim_type: Mapped[str] = mapped_column(String(20), primary_key=True)  # 최장 apartment_complex
    dim_key: Mapped[str] = mapped_column(String(16), primary_key=True)  # 최장 non_apartment
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    value: Mapped[int | None] = mapped_column(BigInteger)  # 세대 수 또는 단지 수
