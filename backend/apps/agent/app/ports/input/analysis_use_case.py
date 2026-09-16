"""Driving Port — AnalysisUseCase 인터페이스 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from apps.agent.domain.entities.agent_event_entity import AgentEvent


class AnalysisUseCase(ABC):
    @abstractmethod
    def run(self, region: str, industry: str, question: str | None) -> Iterator[AgentEvent]:
        """지역×업종(+선택 질문) 분석을 실행하며 SSE 이벤트를 순서대로 흘려보낸다."""
