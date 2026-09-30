from abc import ABC, abstractmethod
from datetime import datetime

from apps.admin.domain.entities.access_event_entity import AccessEvent, AccessEventKind


class AccessEventRepositoryPort(ABC):
    @abstractmethod
    def add(self, event: AccessEvent) -> None: ...

    @abstractmethod
    def list_since(self, since: datetime, limit: int) -> list[AccessEvent]:
        """since 이후 이벤트를 최신순으로 최대 limit건."""

    @abstractmethod
    def count(self, kind: AccessEventKind, ip: str | None, since: datetime) -> int: ...
