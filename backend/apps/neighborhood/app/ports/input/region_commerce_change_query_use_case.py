"""Driving Port — region_commerce_change 조회 UseCase 계약.

적재 UseCase와 나눈다 — 호출자(CLI 대 리포트)도 계약도 다르다 (ISP).
"""

from abc import ABC, abstractmethod

from apps.neighborhood.app.dtos.region_commerce_change_query_dto import (
    RegionCommerceChangeDto,
)


class RegionCommerceChangeQueryUseCase(ABC):
    @abstractmethod
    def find_with_baseline(
        self, region_code: str, year_quarter: str | None
    ) -> RegionCommerceChangeDto | None:
        """상세 — 동×분기 행 + 같은 분기 서울 평균. 분기 생략 시 그 동의 최신. 없으면 None."""
