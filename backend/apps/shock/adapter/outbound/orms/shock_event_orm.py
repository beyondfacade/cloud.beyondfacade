from datetime import date

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class ShockEventOrm(OrmBase):
    """특이변수(외생 충격) — 4계층 유형 시계열 (brainstorming §5.2, docs/erd.md).

    업종 영향은 shock_event_industry, 지역 이벤트(④)는 shock_event_region M:N으로 연결.
    """

    __tablename__ = "shock_event"
    __table_args__ = (
        # 계층별 타임라인 조회(§5.4 충격 구간 정의)가 layer×시행일로 훑는다
        Index("ix_shock_event_layer_start", "layer", "start_date"),
    )

    event_id: Mapped[str] = mapped_column(primary_key=True)  # 결정적 슬러그 — 재적재 멱등
    layer: Mapped[str]  # ShockLayer 값: policy/macro/trend/regional
    name: Mapped[str]
    start_date: Mapped[date]  # 시행일
    end_date: Mapped[date | None]  # 진행 중·상시 효과는 NULL
    scope: Mapped[str]  # 전국/서울/수도권 등
    source: Mapped[str]  # 근거 출처 (기관·고시·API명) — 전 행 필수
    source_url: Mapped[str | None]
    description: Mapped[str | None]  # 지원금 왜곡 주의(§5.2 ⚠️) 등 분석 참고사항
