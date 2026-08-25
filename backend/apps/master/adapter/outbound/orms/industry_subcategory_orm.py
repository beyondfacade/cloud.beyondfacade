from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class IndustrySubcategoryOrm(OrmBase):
    """업종 서브카테고리 — 학원 교습계열, 미용업 세분 등 (brainstorming §3.6)."""

    __tablename__ = "industry_subcategory"

    subcategory_id: Mapped[str] = mapped_column(primary_key=True)  # 예: academy_exam
    industry_id: Mapped[str] = mapped_column(ForeignKey("industry.industry_id"))
    category_axis: Mapped[str]  # 예: 교습계열 / 미용세분
    target_group: Mapped[str | None]  # 대상학년 등 (LLM 추출 축, nullable)
