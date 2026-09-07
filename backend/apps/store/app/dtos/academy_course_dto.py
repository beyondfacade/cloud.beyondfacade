from dataclasses import dataclass

from apps.store.domain.entities.academy_course_entity import AcademyCourse
from apps.store.domain.entities.store_entity import Store


@dataclass
class AcademyRecord:
    """학원 원천 1행의 수집 단위 — 점포(store) + 교습과정 목록(1:N)."""

    store: Store
    courses: list[AcademyCourse]
