"""Driving Port — region_industry_verdict UseCase 인터페이스."""

from abc import ABC, abstractmethod
from datetime import date

from apps.verdict.app.dtos.region_industry_verdict_dto import (
    BacktestReportDto,
    RegionIndustryVerdictDto,
    VerdictAlternativesDto,
    VerdictValueDto,
)


class RegionIndustryVerdictUseCase(ABC):
    @abstractmethod
    def myself(self) -> RegionIndustryVerdictDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def build(self, today: date) -> int:
        """판정 대상 13업종 × 전 행정동 판정을 재계산·업서트하고, 대상 외 업종의 옛 행을 지운 뒤 업서트 건수를 반환한다 (멱등)."""

    @abstractmethod
    def list_verdict_values(self, industry_id: str) -> list[VerdictValueDto]:
        """단계구분도용 — 판정 대상이 아니면 IndustryNotFoundError."""

    @abstractmethod
    def find(self, region_code: str, industry_id: str) -> RegionIndustryVerdictDto | None:
        """카드용 단건 — 없으면 None. 판정 대상이 아니면 IndustryNotFoundError."""

    @abstractmethod
    def alternatives(self, region_code: str, industry_id: str) -> VerdictAlternativesDto | None:
        """대안 두 축 — 기준 판정이 없으면 None. 판정 대상이 아니면 IndustryNotFoundError."""

    @abstractmethod
    def backtest(self, as_of: date, entry_days: int = 365, horizon_days: int = 1095) -> BacktestReportDto:
        """as_of 시점 데이터만으로 판정을 다시 내고 진입 코호트의 실제 폐업과 대조한다 (저장하지 않음, 설계서 §13)."""
