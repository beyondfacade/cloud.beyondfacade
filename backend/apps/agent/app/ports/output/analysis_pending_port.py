from abc import ABC, abstractmethod

from apps.agent.domain.entities.analysis_pending_entity import PendingAnalysis


class AnalysisTargetNotFound(Exception):
    """대기 분석의 지역·업종이 마스터에 없다 — field는 "region" 또는 "industry"."""

    def __init__(self, field: str, value: str) -> None:
        super().__init__(f"{field}: {value}")
        self.field = field
        self.value = value


class PendingAnalysisPort(ABC):
    @abstractmethod
    def save(self, pending: PendingAnalysis) -> None:
        """저장한다. 지역·업종이 마스터에 없으면 AnalysisTargetNotFound."""

    @abstractmethod
    def find(self, analysis_id: str) -> PendingAnalysis | None:
        """수명(PENDING_TTL)이 지난 주문은 없는 것으로 본다."""

    @abstractmethod
    def delete(self, analysis_id: str) -> None: ...
