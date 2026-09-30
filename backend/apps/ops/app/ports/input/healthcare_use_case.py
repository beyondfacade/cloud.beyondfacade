"""Driving Port — 헬스케어실 (LLM·RAG 파이프라인 상태·프로브)."""

from abc import ABC, abstractmethod

from apps.ops.app.dtos.healthcare_dto import HealthcareSnapshotDto, LlmRouteDto, ProbeResultDto


class UnknownProbeKind(ValueError):
    pass


class HealthcareUseCase(ABC):
    @abstractmethod
    def myself(self) -> LlmRouteDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def snapshot(self) -> HealthcareSnapshotDto: ...

    @abstractmethod
    def probe(self, kind: str, message: str) -> ProbeResultDto:
        """kind = rag | llm. 모르는 kind는 UnknownProbeKind."""
