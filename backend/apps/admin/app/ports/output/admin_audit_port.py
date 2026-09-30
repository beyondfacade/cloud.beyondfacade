from abc import ABC, abstractmethod
from datetime import datetime

from apps.admin.domain.entities.admin_audit_entity import AdminAudit, AuditAction


class AdminAuditRepositoryPort(ABC):
    @abstractmethod
    def add(self, entry: AdminAudit) -> None: ...

    @abstractmethod
    def page(self, action: AuditAction | None, before_id: int | None, limit: int) -> list[AdminAudit]:
        """id 역순(최신순)으로 before_id보다 작은 항목을 최대 limit건."""

    @abstractmethod
    def delete_before(self, cutoff: datetime) -> int: ...
