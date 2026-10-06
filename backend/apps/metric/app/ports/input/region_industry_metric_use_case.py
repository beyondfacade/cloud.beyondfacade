"""Driving Port — region_industry_metric UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.metric.app.dtos.region_industry_metric_dto import RegionIndustryMetricDto


class RegionIndustryMetricUseCase(ABC):
    @abstractmethod
    def build(self, years: list[int]) -> int:
        """연도 범위의 지표를 store 원천 집계 + 스냅샷 원천 현행 점포수로 재계산·업서트하고 처리 건수를 반환한다 (멱등)."""

    @abstractmethod
    def find(
        self, region_code: str, industry_id: str, year: int
    ) -> RegionIndustryMetricDto | None:
        """단건 조회 — 없으면 None (region summary 카드용)."""
