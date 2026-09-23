"""Driving Port — intent UseCase 계약."""

from abc import ABC, abstractmethod

from apps.intent.app.dtos.intent_dto import IntentResultDto


class IntentUseCase(ABC):
    @abstractmethod
    def myself(self) -> IntentResultDto:
        """배선 검증용 — 하드코딩 A유형 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def parse(self, text: str) -> IntentResultDto:
        """한 문장 → 의도. 규칙이 먼저, region 결측일 때만 LLM. 빈 문장은 IntentTextEmptyError."""

    @abstractmethod
    def diagnose(self, region_code: str, industry_id: str) -> IntentResultDto:
        """두 번째 형태 — 되묻기 칩으로 완성된 A유형에 진단만 붙인다. 파서를 건너뛴다."""
