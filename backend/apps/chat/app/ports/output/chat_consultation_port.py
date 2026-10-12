"""Driven Port — 전문가 상담 구매 기록."""

from abc import ABC, abstractmethod
from datetime import datetime

from apps.chat.domain.entities.chat_consultation_entity import ChatConsultation


class ChatConsultationRepositoryPort(ABC):
    @abstractmethod
    def add(self, consultation: ChatConsultation) -> ChatConsultation: ...

    @abstractmethod
    def holders(self, now: datetime) -> dict[int, int]:
        """지금 상담 중인 전문가 id → 그 상담을 산 회원 id."""
