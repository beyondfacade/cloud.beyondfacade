from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from apps.childcare.adapter.outbound.orms import childcare_center_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class ChildcareCenterStatOrm(OrmBase):
    """어린이집 기준일별 정원·현원·대기 현황 — 가동률 추이·수요 초과 관측용 이력.

    시설 행에 덮어쓰지 않는 근거: 현원·대기는 시점마다 변해 덮어쓰면 추이가 복구 불가로
    소실된다. PK(center_id, base_date)라 같은 기준일 재수집은 멱등.
    """

    __tablename__ = "childcare_center_stat"

    center_id: Mapped[str] = mapped_column(
        ForeignKey("childcare_center.center_id"), primary_key=True
    )
    base_date: Mapped[date] = mapped_column(primary_key=True)  # datastdrdt 원천 기준일
    capacity: Mapped[int]  # 정원
    child_count: Mapped[int]  # 현원
    waiting_count: Mapped[int | None]  # 입소대기 — 원천 공란은 NULL 보존
    class_count: Mapped[int]  # 반 수
    staff_count: Mapped[int]  # 보육교직원 수
