from abc import ABC, abstractmethod
from datetime import datetime

from apps.admin.domain.entities.admin_session_entity import AdminSession


class AdminSessionRepositoryPort(ABC):
    @abstractmethod
    def add(self, session: AdminSession) -> None: ...

    @abstractmethod
    def get(self, token_hash: str) -> AdminSession | None: ...

    @abstractmethod
    def delete(self, token_hash: str) -> None: ...

    @abstractmethod
    def list_active_for_user(self, user_id: int, now: datetime) -> list[AdminSession]:
        """만료되지 않은 세션을 최근 발급순으로."""

    @abstractmethod
    def delete_for_user(self, user_id: int, keep_token_hash: str | None = None) -> int:
        """그 계정의 세션을 모두 지운다 — keep_token_hash는 남긴다(지금 쓰는 내 세션)."""

    @abstractmethod
    def count_active_by_user(self, now: datetime) -> dict[int, int]: ...

    @abstractmethod
    def delete_expired(self, now: datetime) -> int: ...
