from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
import apps.shock.adapter.outbound.orms.shock_event_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class ShockEventRegionOrm(OrmBase):
    """충격×행정동 M:N — ④지역 이벤트 계층용 자리 (brainstorming §5.2).

    MVP는 빈 테이블 허용 — 뉴스 기반 ④계층 감지(§5.3)가 행을 채우는 후속 작업.
    """

    __tablename__ = "shock_event_region"

    event_id: Mapped[str] = mapped_column(
        ForeignKey("shock_event.event_id"), primary_key=True
    )
    region_code: Mapped[str] = mapped_column(
        ForeignKey("region.region_code"), primary_key=True
    )
