from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionProfileQuarterOrm(OrmBase):
    """행정동×분기 동네 프로필 — 배치 재생성 가능한 파생 계층 (설계서 §4-1).

    값 컬럼을 넓은 형태로 두는 이유는 이들이 반복 그룹이 아니라 **서로 다른 측정값**이기
    때문이다. 긴 형태로 내리면 "직장비와 주말지수를 같이 보여달라"가 self-join이 된다.

    지표 6개를 판정과 함께 저장하는 것은 의도한 역정규화다. 화면이 근거를 보여줘야 하는데
    판정만 있으면 999만 행에서 다시 계산해야 한다.
    """

    __tablename__ = "region_profile_quarter"
    __table_args__ = (
        # 지도 레이어가 한 분기의 전 행정동 유형을 훑는다
        Index("ix_region_profile_quarter_quarter_type", "year_quarter", "neighborhood_type"),
    )

    region_code: Mapped[str] = mapped_column(
        ForeignKey("region.region_code"), primary_key=True
    )
    year_quarter: Mapped[str] = mapped_column(String(5), primary_key=True)  # '20251'
    # 최장 residential
    neighborhood_type: Mapped[str] = mapped_column(String(12))
    type_reason: Mapped[str] = mapped_column(Text)  # 화면에 그대로 띄우는 근거 문장
    time_label: Mapped[str | None] = mapped_column(String(8))  # morning|day|evening|night|flat
    peak_block: Mapped[str | None] = mapped_column(String(8))
    trough_block: Mapped[str | None] = mapped_column(String(8))
    # 직장인구 결측 11개 동은 NULL — 0으로 채우면 주거형으로 오판한다 (설계서 §3-4)
    worker_resident_ratio: Mapped[float | None] = mapped_column(Float)
    weekend_index: Mapped[float | None] = mapped_column(Float)
    night_index: Mapped[float | None] = mapped_column(Float)  # 00_06 시간강도
    footfall_20s_share: Mapped[float | None] = mapped_column(Float)
    fnb_share: Mapped[float | None] = mapped_column(Float)
    facility_total: Mapped[int | None] = mapped_column(Integer)
    resident_total: Mapped[int | None] = mapped_column(Integer)
