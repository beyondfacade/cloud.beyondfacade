"""Driving Port — region_industry_hour_gap UseCase 인터페이스 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.metric.app.dtos.region_industry_hour_gap_dto import RegionIndustryHourGapDto


class RegionIndustryHourGapUseCase(ABC):
    @abstractmethod
    def myself(self) -> RegionIndustryHourGapDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def build(self, quarters: list[str]) -> int:
        """분기 목록의 시간대 어긋남을 재계산·업서트하고 처리 건수를 반환한다 (멱등)."""

    @abstractmethod
    def list_bands(
        self, region_code: str, industry_id: str, year_quarter: str
    ) -> list[RegionIndustryHourGapDto]:
        """해당 동×업종×분기의 6구간을 시간 순으로 반환한다 (없으면 빈 리스트)."""
