from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

import apps.master.adapter.outbound.orms.region_orm  # noqa: F401  FK 대상 메타데이터 보장
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionFootfallQuarterOrm(OrmBase):
    """유동인구 — 1NF long (OA-22178, 설계서 §4-1). 원본 1행 → 22행.

    wide 25컬럼으로 두지 않는 근거는 commerce 분해와 같다: 축이 늘 때마다 DDL이 필요하고
    "시간대 상위 구간" 질의가 컬럼 UNION이 된다. (dim_type, dim_key)를 값으로 내리면 축 추가가
    적재만으로 끝난다.

    `region_code`는 8자리↔10자리 `left()` 조인을 피하기 위한 의도적 역정규화이며(ERD §13 엣지
    + 인덱스 활용), 원천에만 있는 옛 행정동 3개는 NULL로 남는다.
    """

    __tablename__ = "region_footfall_quarter"
    __table_args__ = (
        Index(
            "ix_region_footfall_quarter_region",
            "region_code",
            "year_quarter",
            "dim_type",
        ),
    )

    adstrd_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)  # '20251'
    dim_type: Mapped[str] = mapped_column(String(16), primary_key=True)
    dim_key: Mapped[str] = mapped_column(String(16), primary_key=True)
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    headcount: Mapped[int | None] = mapped_column(BigInteger)
