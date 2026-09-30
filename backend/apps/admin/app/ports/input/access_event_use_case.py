"""Driving Port — 보안 이벤트 기록·보안감사 개요."""

from abc import ABC, abstractmethod

from apps.admin.app.dtos.access_event_dto import SecurityOverviewDto
from apps.admin.domain.entities.access_event_entity import AccessEventKind


class AccessEventUseCase(ABC):
    @abstractmethod
    def myself(self) -> SecurityOverviewDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def record(self, kind: AccessEventKind, ip: str | None, method: str, path: str, status_code: int) -> None: ...

    @abstractmethod
    def overview(self) -> SecurityOverviewDto:
        """최근 24시간 이벤트 요약 + 규칙 기반 알림 + 최근 이벤트 50건."""
