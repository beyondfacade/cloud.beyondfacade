"""Driving Port — region_commerce_change 조회 UseCase 계약.

적재 UseCase와 나눈다 — 호출자(CLI 대 라우터)도 계약도 다르다 (ISP).
"""

from abc import ABC, abstractmethod

from apps.neighborhood.app.dtos.region_commerce_change_query_dto import (
    ChangeMetricValueDto,
    RegionCommerceChangeDto,
)


class RegionCommerceChangeQueryUseCase(ABC):
    @abstractmethod
    def myself(self) -> RegionCommerceChangeDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def list_metric_values(
        self, metric: str, year_quarter: str | None
    ) -> list[ChangeMetricValueDto]:
        """단계구분도용 — 해당 분기의 행정동별 지표값 (값 None 행 제외).

        분기를 생략하면 가장 최근 분기를 쓴다. 미지원 metric은 MetricNotFoundError.
        """
