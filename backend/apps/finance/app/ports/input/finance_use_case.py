"""Driving Port — finance UseCase 계약."""

from abc import ABC, abstractmethod

from apps.finance.app.dtos.finance_dto import (
    FinanceInputDto,
    FinanceResultDto,
    PrefillDto,
    QuestionDto,
    QuestionRequestDto,
)


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

    @abstractmethod
    def questions(self, request: QuestionRequestDto) -> list[QuestionDto]:
        """확인할 질문 초안 — 계획 수치에서 결정론으로 만든다 (설계서 §4).

        서버가 결과를 다시 계산한다. 사용자가 편집·삭제·추가하는 초안일 뿐이다.
        """
