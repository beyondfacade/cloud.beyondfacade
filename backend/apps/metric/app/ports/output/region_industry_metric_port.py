"""Driven Ports — metric이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.metric.app.dtos.region_industry_metric_dto import YearlyStoreStat
from apps.metric.domain.entities.region_industry_metric_entity import (
    RegionIndustryMetric,
)


class RegionIndustryMetricRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, metrics: list[RegionIndustryMetric]) -> int:
        """(region_code, industry_id, year) 기준 업서트 — 처리 건수 반환."""

    @abstractmethod
    def list_by_industry_year(
        self, industry_id: str, year: int
    ) -> list[RegionIndustryMetric]:
        """해당 업종×연도의 전 행정동 지표를 region_code 순으로 반환한다."""

    @abstractmethod
    def find(
        self, region_code: str, industry_id: str, year: int
    ) -> RegionIndustryMetric | None:
        """복합키 단건 조회 — 없으면 None."""


class StoreStatsPort(ABC):
    @abstractmethod
    def yearly_stats(self, years: list[int]) -> list[YearlyStoreStat]:
        """연도별 행정동×업종 store 원천 카운트 (region_code 보유 점포만)."""


class IndustryCatalogPort(ABC):
    @abstractmethod
    def exists(self, industry_id: str) -> bool:
        """industry 마스터 등록 여부."""
