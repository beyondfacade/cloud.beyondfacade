"""Driving Port — 관리자 조치 감사 로그."""

from abc import ABC, abstractmethod

from apps.admin.app.dtos.admin_audit_dto import AuditPageDto
from apps.admin.app.dtos.admin_session_dto import AdminPrincipalDto
from apps.admin.domain.entities.admin_audit_entity import AuditAction


class AdminAuditUseCase(ABC):
    @abstractmethod
    def myself(self) -> AuditPageDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def record(
        self, actor: AdminPrincipalDto, action: AuditAction, target: str, detail: str = "", ip: str | None = None
    ) -> None:
        """다른 BC(ops)의 조치도 여기로 남긴다."""

    @abstractmethod
    def page(self, action: AuditAction | None, before_id: int | None, limit: int) -> AuditPageDto: ...
