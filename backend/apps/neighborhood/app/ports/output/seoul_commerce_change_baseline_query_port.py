"""Driven Port — seoul_commerce_change_baseline 조회 계약.

상권 변화 조회 포트와 나눈다 — 다른 테이블이고, 필요한 쪽(상세 응답)만 이 포트를 받는다 (ISP).
"""

from abc import ABC, abstractmethod

from apps.neighborhood.domain.entities.seoul_commerce_change_baseline_entity import (
    SeoulCommerceChangeBaseline,
)


class SeoulCommerceChangeBaselineQueryPort(ABC):
    @abstractmethod
    def find(self, year_quarter: str) -> SeoulCommerceChangeBaseline | None:
        """해당 분기의 서울 전체 평균 — 없으면 None."""
