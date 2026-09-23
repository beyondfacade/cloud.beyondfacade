from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

import apps.master.adapter.outbound.orms.industry_orm  # noqa: F401
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionIndustryHourGapQuarterOrm(OrmBase):
    """행정동×업종×분기×시간구간 어긋남 — 배치 재생성 가능한 파생 계층 (설계서 §4-2).

    단일 점수로 뭉개지 않고 구간을 행으로 펴는 이유는 화면이 최대·최소 구간만 뽑아 문장을 만들기
    때문이다. "사람은 출근길에 가장 많은데 돈은 오후에 쓴다"를 말하려면 어느 구간인지가 필요하다.

    강도 둘을 gap과 함께 저장하는 것은 의도한 역정규화다. 어긋남의 크기만으로는 "사람이 없는데
    돈이 돈다"와 "사람도 돈도 많다"를 구분할 수 없다.
    """

    __tablename__ = "region_industry_hour_gap_quarter"
    __table_args__ = (
        # 사이드패널이 한 동·한 분기의 전 업종을 훑는다 (PK 선두는 region_code 하나뿐)
        Index(
            "ix_region_industry_hour_gap_quarter_region_quarter",
            "region_code",
            "year_quarter",
        ),
    )

    region_code: Mapped[str] = mapped_column(
        ForeignKey("region.region_code"), primary_key=True
    )
    industry_id: Mapped[str] = mapped_column(
        ForeignKey("industry.industry_id"), primary_key=True
    )
    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)
    hour_band: Mapped[str] = mapped_column(String(5), primary_key=True)  # '00_06'
    footfall_intensity: Mapped[float] = mapped_column(Float)  # 1.0 = 24시간 균등
    sales_intensity: Mapped[float] = mapped_column(Float)
    gap: Mapped[float] = mapped_column(Float)  # sales − footfall
