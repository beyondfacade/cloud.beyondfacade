from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.industry_orm  # noqa: F401
import apps.shock.adapter.outbound.orms.shock_event_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class ShockEventIndustryOrm(OrmBase):
    """충격×업종 M:N — 업종별 영향도 (brainstorming §5.2 표: 노래방·PC방·헬스장 ≫ 카페)."""

    __tablename__ = "shock_event_industry"

    event_id: Mapped[str] = mapped_column(
        ForeignKey("shock_event.event_id"), primary_key=True
    )
    industry_id: Mapped[str] = mapped_column(
        ForeignKey("industry.industry_id"), primary_key=True
    )
    severity: Mapped[str]  # Severity 값: critical/high/medium/low
