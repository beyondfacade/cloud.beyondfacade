"""Driving Port — 헬스케어실 (LLM·RAG 파이프라인 상태·프로브)."""

from abc import ABC, abstractmethod

from apps.ops.app.dtos.healthcare_dto import HealthcareSnapshotDto, LlmRouteDto, ProbeResultDto
from apps.ops.app.dtos.ops_history_dto import OpsActorDto, UsageSeriesDto


class UnknownProbeKind(ValueError):
    pass


class HealthcareUseCase(ABC):
    @abstractmethod
    def myself(self) -> LlmRouteDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def snapshot(self) -> HealthcareSnapshotDto: ...

    @abstractmethod
    def probe(self, kind: str, message: str, actor: OpsActorDto) -> ProbeResultDto:
        """kind = rag | llm. 모르는 kind는 UnknownProbeKind. 실행은 감사 로그에 남는다."""

    @abstractmethod
    def usage_series(self, hours: int) -> UsageSeriesDto:
        """hours = 24 | 168. 분석 건수·토큰과 LLM 호출 결과(성공·폴백·오류)를 시간 버킷으로."""
