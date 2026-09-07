from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(store) 테이블이 메타데이터에 항상 존재하도록 보장
import apps.store.adapter.outbound.orms.store_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class AcademyCourseOrm(OrmBase):
    """교습과정 (학원 store 1:N) — 서울 학원·교습소 OA-20528 실응답 기반 (2026-09-07 검증)."""

    __tablename__ = "academy_course"

    course_id: Mapped[str] = mapped_column(primary_key=True)  # f"{store_id}:{연번}"
    store_id: Mapped[str] = mapped_column(ForeignKey("store.store_id"), index=True)
    course_name: Mapped[str]  # 수강료 항목명(INDV_ATNLC_AMT_CN) 또는 교습과정명(TRNG_CRS_LIST_NM)
    tuition_fee: Mapped[int | None]  # 수강료(원) — 미공개 항목은 NULL
    target_grade: Mapped[str | None]  # 대상학년 — LLM 추출 후속, 현재 NULL
