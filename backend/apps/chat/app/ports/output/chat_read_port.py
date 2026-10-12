"""Driven Port — 방별로 어디까지 읽었는지."""

from abc import ABC, abstractmethod
from datetime import datetime


class ChatReadRepositoryPort(ABC):
    @abstractmethod
    def last_read_ids(self, user_id: int) -> dict[str, int]: ...

    @abstractmethod
    def advance(self, user_id: int, room: str, last_read_id: int, at: datetime) -> int:
        """앞으로만 간다 — 더 작은 값이 와도 저장된 값을 지키고, 저장된 값을 돌려준다."""
