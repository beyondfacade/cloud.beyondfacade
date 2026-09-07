from dataclasses import dataclass


@dataclass
class AcademyCourse:
    """교습과정 (학원 store 1:N) — 수강료 공개 항목 또는 교습과정명 단위."""

    course_id: str  # f"{store_id}:{연번}"
    store_id: str
    course_name: str  # 원문 보존 — 대상학년 LLM 추출 원천 (후속 범위)
    tuition_fee: int | None  # 수강료(원) — 미공개·과정명만 있는 항목은 None
    target_grade: str | None = None  # LLM 추출 후속 — 현재 항상 None
