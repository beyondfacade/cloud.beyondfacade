from abc import ABC, abstractmethod

from apps.agent.domain.entities.llm_call_entity import LlmCall


class LlmCallRecorderPort(ABC):
    @abstractmethod
    def record(self, call: LlmCall) -> None: ...
