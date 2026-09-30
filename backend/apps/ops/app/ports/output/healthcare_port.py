"""Driven Ports — 헬스케어실이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from datetime import datetime

from apps.ops.app.dtos.healthcare_dto import (
    LlmRouteDto,
    OllamaStatusDto,
    ProbeResultDto,
    RagStatsDto,
    RecentAnalysisDto,
)
from apps.ops.domain.services.usage_stats import LlmUsageRecord


class OllamaStatusPort(ABC):
    @abstractmethod
    def read(self) -> OllamaStatusDto:
        """연결 실패도 예외 없이 reachable=False로 돌려준다."""


class LlmChainPort(ABC):
    @abstractmethod
    def routes(self) -> list[LlmRouteDto]:
        """분석 에이전트 기본 배선(hybrid)의 LLM 순서 — 가용성은 설정 기준."""

    @abstractmethod
    def required_ollama_models(self) -> list[tuple[str, str]]:
        """(모델명, 용도) — 로컬 폴백 LLM과 RAG 검색 임베더."""


class LlmUsagePort(ABC):
    @abstractmethod
    def records_since(self, since: datetime) -> list[LlmUsageRecord]: ...

    @abstractmethod
    def recent_analyses(self, limit: int) -> list[RecentAnalysisDto]: ...


class RagStatsPort(ABC):
    @abstractmethod
    def read(self) -> RagStatsDto: ...


class ProbePort(ABC):
    @abstractmethod
    def run(self, message: str) -> ProbeResultDto:
        """실패도 예외 없이 ok=False·error로 돌려준다."""
