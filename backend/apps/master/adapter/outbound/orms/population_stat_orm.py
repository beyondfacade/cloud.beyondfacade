from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class PopulationStatOrm(OrmBase):
    """행정동×연월×성별×연령구간 주민등록 인구 — 원천 계층, long format (docs/erd.md §3 1NF).

    원천: 행안부 주민등록 연령별 인구현황 CSV (data/raw/jumin/연령별*.csv, 5세 구간).
    계(합계)·총인구수는 남/여 합산으로 도출 가능하므로 저장하지 않는다 (3NF).
    """

    __tablename__ = "population_stat"
    __table_args__ = (
        # 특정 연월의 전 행정동 스캔(연령 분포·학령인구 집계)이 period로 훑는다
        Index("ix_population_stat_period", "period"),
    )

    region_code: Mapped[str] = mapped_column(
        ForeignKey("region.region_code"), primary_key=True
    )
    period: Mapped[str] = mapped_column(primary_key=True)  # YYYYMM
    gender: Mapped[str] = mapped_column(primary_key=True)  # 'M'/'F'
    age_from: Mapped[int] = mapped_column(primary_key=True)  # 5세 구간 시작: 0,5,…,100
    age_to: Mapped[int | None]  # 구간 끝 (100세 이상 = None)
    population: Mapped[int]
