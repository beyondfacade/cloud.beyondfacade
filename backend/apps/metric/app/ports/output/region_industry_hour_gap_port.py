"""Driven Ports — region_industry_hour_gap이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.metric.app.dtos.region_industry_hour_gap_dto import (
    RegionHourValues,
    RegionIndustryHourSales,
)
from apps.metric.domain.entities.region_industry_hour_gap_entity import (
    RegionIndustryHourGap,
)


class RegionIndustryHourGapRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, gaps: list[RegionIndustryHourGap]) -> int:
        """(region_code, industry_id, year_quarter, hour_band) 기준 업서트 — 처리 건수 반환."""

    @abstractmethod
    def list_bands(
        self, region_code: str, industry_id: str, year_quarter: str
    ) -> list[RegionIndustryHourGap]:
        """해당 동×업종×분기의 6구간을 시간 순으로 반환한다."""

    @abstractmethod
    def latest_quarter(self, region_code: str, industry_id: str) -> str | None:
        """그 동×업종에 어긋남 행이 있는 가장 최근 분기 — 없으면 None. 매출 원천은 20254까지다."""


class RegionFootfallHourPort(ABC):
    @abstractmethod
    def hour_values(self, quarters: list[str]) -> list[RegionHourValues]:
        """해당 분기들의 행정동별 시간대 유동인구 원값."""


class RegionIndustryHourSalesPort(ABC):
    @abstractmethod
    def hour_sales(self, quarters: list[str]) -> list[RegionIndustryHourSales]:
        """해당 분기들의 행정동×업종별 시간대 매출 원값 (다중 CS 코드는 합산 후)."""
