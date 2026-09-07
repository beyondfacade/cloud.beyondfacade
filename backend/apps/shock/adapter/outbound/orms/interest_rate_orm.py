from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class InterestRateOrm(OrmBase):
    """금리 시계열 — 계산기·부동산 분석 공용 독립 시계열 (docs/erd.md §4 역정규화 근거).

    상권과 무관한 전국 공시 데이터 — region/industry와 직접 엣지 없이
    계산기 유스케이스에서 rent_price와 애플리케이션 조인한다.
    원천: 한국은행 ECOS StatisticSearch 722Y001(월)/0101000 기준금리.
    """

    __tablename__ = "interest_rate"
    __table_args__ = (
        # 계산기·시계열 차트가 유형×연월로 조회한다
        Index("ix_interest_rate_type_period", "rate_type", "period"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)  # "{rate_type}:{period}"
    rate_type: Mapped[str]  # "base" 기준금리 — 가중평균 대출금리(121Y006) 확장 대비
    period: Mapped[str]  # YYYYMM
    rate: Mapped[float]  # 연% 값
    unit: Mapped[str]  # ECOS UNIT_NAME ("연%")
    stat_code: Mapped[str]  # ECOS 통계코드
    item_code: Mapped[str]  # ECOS 항목코드
