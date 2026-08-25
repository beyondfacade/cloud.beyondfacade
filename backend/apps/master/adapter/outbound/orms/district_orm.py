from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class DistrictOrm(OrmBase):
    """자치구 (서울 25개) — 행정기관코드 앞 5자리."""

    __tablename__ = "district"

    district_code: Mapped[str] = mapped_column(primary_key=True)  # 예: 11110 (종로구)
    name: Mapped[str]
    # 행안부 인허가 API의 개방자치단체코드 (예: 3000000 종로구) — 2026-08-25 실호출로 25개 구 전수 확인
    opn_authority_code: Mapped[str | None] = mapped_column(unique=True)
