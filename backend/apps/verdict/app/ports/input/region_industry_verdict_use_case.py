"""Driving Port — region_industry_verdict UseCase 인터페이스."""

from abc import ABC, abstractmethod
from datetime import date

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    RegionIndustryVerdictDto,
    VerdictValueDto,
)


class RegionIndustryVerdictUseCase(ABC):
    @abstractmethod
    def myself(self) -> RegionIndustryVerdictDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def build(self, today: date) -> int:
        """판정 대상 14업종 × 전 행정동 판정을 재계산·업서트하고 처리 건수를 반환한다 (멱등)."""

    @abstractmethod
    def list_verdict_values(self, industry_id: str) -> list[VerdictValueDto]:
        """단계구분도용 — 판정 대상이 아니면 IndustryNotFoundError."""

    @abstractmethod
    def find(self, region_code: str, industry_id: str) -> RegionIndustryVerdictDto | None:
        """카드용 단건 — 없으면 None. 판정 대상이 아니면 IndustryNotFoundError."""
