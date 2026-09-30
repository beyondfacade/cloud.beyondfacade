"""Driving Port — 유사 사례 UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.shock.app.dtos.event_analog_dto import EventAnalogReportDto


class EventAnalogUseCase(ABC):
    @abstractmethod
    def myself(self) -> EventAnalogReportDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def analogs(self, industry_id: str, question: str | None) -> EventAnalogReportDto:
        """진행 중 이벤트와 질문 속 유형의 지난 사례 — 유형의 비교 기간 동안 분기마다 업종 변동폭."""
