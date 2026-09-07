from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class RentPriceOrm(OrmBase):
    """상가 임대시세 — R-ONE 상업용부동산 임대동향조사, 분기 (계산기 §8.1③ 임대료 축).

    지역 단위는 자치구가 아니라 R-ONE 상권/권역/시도(2026-09-07 실호출 확인:
    CLS_FULLNM "서울>강남>테헤란로") — 원천 지역명을 보존하고 district FK는
    nullable(의도된 미연결: 상권이 자치구 경계와 불일치, 매핑은 후속).
    임대료·공실률이 별도 통계표로 오므로 같은 PK 행에 병합 적재한다.
    """

    __tablename__ = "rent_price"
    __table_args__ = (
        # 계산기·시계열 차트가 상가유형×분기로 조회한다
        Index("ix_rent_price_type_period", "building_type", "period"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)  # "{building_type}:{cls_id}:{period}"
    building_type: Mapped[str]  # "medium_large" 중대형 상가 / "small" 소규모 상가
    cls_id: Mapped[str]  # R-ONE 지역 분류 ID (CLS_ID)
    region_name: Mapped[str]  # CLS_NM 원문
    region_path: Mapped[str]  # CLS_FULLNM 원문 "서울>권역>상권"
    region_level: Mapped[int]  # 1 시도 / 2 권역 / 3 상권
    # 상권 단위 원천이라 자치구 미확정 — 후속 상권→자치구 매핑 시 채움 (erd.md nullable FK 사유)
    district_code: Mapped[str | None] = mapped_column(ForeignKey("district.district_code"))
    period: Mapped[str]  # "YYYYQn" 분기
    rent_per_m2: Mapped[float | None]  # 임대료 (천원/㎡)
    vacancy_rate: Mapped[float | None]  # 공실률 (%)
    rent_statbl_id: Mapped[str | None]  # 임대료 값의 R-ONE 통계표 ID (표본 개편 추적)
    vacancy_statbl_id: Mapped[str | None]  # 공실률 값의 R-ONE 통계표 ID
