from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionPopulationQuarterOrm(OrmBase):
    """직장·상주인구 — 1NF long (OA-22184 · OA-22183, 설계서 §4-2). 원본 1행 → 21행.

    두 원천의 값 컬럼 21개가 한 글자도 다르지 않아(설계서 §3-3) `population_type` 하나로
    구분한다. 테이블을 둘로 나누면 같은 스키마가 두 벌이 되고 "동네 인구 구성" 질의가 UNION이
    된다.

    **직장인구는 414개 동뿐이다(11개 부족).** 없는 동의 행을 만들지 않으므로 상주와 조인할 때
    내부 조인을 쓰면 동이 조용히 줄어든다 — LEFT JOIN + NULL이 원칙이다(설계서 §3-2).
    """

    __tablename__ = "region_population_quarter"
    __table_args__ = (
        Index(
            "ix_region_population_quarter_region",
            "region_code",
            "year_quarter",
            "population_type",
            "dim_type",
        ),
    )

    adstrd_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)
    population_type: Mapped[str] = mapped_column(String(8), primary_key=True)  # worker|resident
    dim_type: Mapped[str] = mapped_column(String(16), primary_key=True)
    dim_key: Mapped[str] = mapped_column(String(16), primary_key=True)
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    headcount: Mapped[int | None] = mapped_column(BigInteger)
