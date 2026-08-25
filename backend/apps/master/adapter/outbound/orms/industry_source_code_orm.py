from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class IndustrySourceCodeOrm(OrmBase):
    """업종 ↔ 원천 데이터소스 코드 매핑 (docs/api.md 확정 코드만 시드)."""

    __tablename__ = "industry_source_code"
    __table_args__ = (UniqueConstraint("industry_id", "source_system", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industry.industry_id"))
    source_system: Mapped[str]  # 예: mois_permit(행안부 인허가) / seoul_academy / childcare_portal
    code: Mapped[str]  # 예: 인허가 업종슬러그(karaoke_rooms), 데이터셋 ID(OA-20528)
