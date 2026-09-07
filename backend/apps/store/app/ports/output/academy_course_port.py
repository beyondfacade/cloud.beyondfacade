"""Driven Ports — 학원(academy_course) 수집이 바깥 세계에 요구하는 계약."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from apps.store.app.dtos.academy_course_dto import AcademyRecord
from apps.store.domain.entities.academy_course_entity import AcademyCourse


class AcademyGatewayPort(ABC):
    @abstractmethod
    def iter_academies(self) -> Iterator[AcademyRecord]:
        """원천(서울 학원·교습소)을 페이징 순회하며 점포+교습과정으로 반환한다."""


class AcademyCourseRepositoryPort(ABC):
    @abstractmethod
    def replace_for_stores(self, courses_by_store: dict[str, list[AcademyCourse]]) -> int:
        """해당 점포들의 교습과정을 전량 교체(delete+insert 재적재, 멱등) — 삽입 건수 반환."""
