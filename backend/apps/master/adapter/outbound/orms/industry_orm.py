from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class IndustryOrm(OrmBase):
    """타겟 업종 10종 — 수요동인 4유형 (brainstorming §3.5)."""

    __tablename__ = "industry"

    industry_id: Mapped[str] = mapped_column(primary_key=True)  # 예: cafe
    name: Mapped[str]
    demand_type: Mapped[str]  # daily(일상소비) / leisure(여가) / macro(경기민감) / demographic(인구구조)
