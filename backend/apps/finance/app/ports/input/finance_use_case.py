"""Driving Port — finance UseCase 계약."""

from abc import ABC, abstractmethod

from apps.finance.app.dtos.finance_dto import FinanceInputDto, FinanceResultDto, PrefillDto


class FinanceUseCase(ABC):
    @abstractmethod
    def myself(self) -> FinanceResultDto:
        """배선 검증용 — 하드코딩 입력을 엔진에 실제로 통과시켜 왕복한다 (CLAUDE.md §12)."""

    @abstractmethod
    def simulate(self, request: FinanceInputDto) -> FinanceResultDto:
        """서버가 계산한다. 클라이언트 계산 결과를 신뢰하지 않는다."""

    @abstractmethod
    def prefill(self, region_code: str, industry_id: str) -> PrefillDto:
        """실측 프리필 — 값마다 출처와 단서. RegionNotFoundError / IndustryNotFoundError."""
