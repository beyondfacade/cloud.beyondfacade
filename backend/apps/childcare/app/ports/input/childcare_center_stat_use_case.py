"""Driving Port — 어린이집 현황 조회 UseCase 계약."""

from abc import ABC, abstractmethod

from apps.childcare.app.dtos.childcare_center_stat_dto import ChildcareRegionSummaryDto


class ChildcareCenterStatUseCase(ABC):
    @abstractmethod
    def myself(self) -> ChildcareRegionSummaryDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def summarize_region(self, region_code: str) -> ChildcareRegionSummaryDto:
        """행정동의 운영 중 시설 최신 현황 합계. 미등록 행정동은 RegionNotFoundError."""
