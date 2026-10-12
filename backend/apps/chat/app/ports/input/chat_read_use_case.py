"""Driving Port — 읽음 표시 (안 읽은 개수의 기준)."""

from abc import ABC, abstractmethod

from apps.chat.app.dtos.chat_read_dto import ChatReadDto
from apps.chat.domain.value_objects.chat_room import ChatMember


class ChatReadUseCase(ABC):
    @abstractmethod
    def myself(self) -> ChatReadDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def mark_read(self, member: ChatMember, room_key: str, last_read_id: int) -> ChatReadDto: ...
