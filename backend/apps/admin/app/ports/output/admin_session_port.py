from abc import ABC, abstractmethod

from apps.admin.domain.entities.admin_session_entity import AdminSession


class AdminSessionRepositoryPort(ABC):
    @abstractmethod
    def add(self, session: AdminSession) -> None: ...

    @abstractmethod
    def get(self, token_hash: str) -> AdminSession | None: ...

    @abstractmethod
    def delete(self, token_hash: str) -> None: ...
