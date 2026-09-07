"""Driving Port — region_industry_metric UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.metric.app.dtos.region_industry_metric_dto import (
    MetricValueDto,
    RegionIndustryMetricDto,
)


class RegionIndustryMetricUseCase(ABC):
    @abstractmethod
    def myself(self) -> RegionIndustryMetricDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def build(self, years: list[int]) -> int:
        """연도 범위의 지표를 store 원천 집계로 재계산·업서트하고 처리 건수를 반환한다 (멱등)."""

    @abstractmethod
    def list_metric_values(
        self, industry_id: str, metric: str, year: int
    ) -> list[MetricValueDto]:
        """단계구분도용 — 해당 업종×연도의 행정동별 지표값 (값 None 행 제외).

        미지원 metric은 MetricNotFoundError, 미등록 업종은 IndustryNotFoundError.
        """

    @abstractmethod
    def find(
        self, region_code: str, industry_id: str, year: int
    ) -> RegionIndustryMetricDto | None:
        """단건 조회 — 없으면 None (region summary 카드용)."""
