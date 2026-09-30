"""Driving Port — 보안 이벤트 기록·보안감사 개요."""

from abc import ABC, abstractmethod

from apps.admin.app.dtos.access_event_dto import AccessEventPageDto, SecurityOverviewDto
from apps.admin.domain.entities.access_event_entity import AccessEventKind
from apps.admin.domain.entities.client_entity import Client


class AccessEventUseCase(ABC):
    @abstractmethod
    def myself(self) -> SecurityOverviewDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def record(self, kind: AccessEventKind, client: Client, method: str, path: str, status_code: int) -> None: ...

    @abstractmethod
    def overview(self) -> SecurityOverviewDto:
        """최근 24시간 이벤트 요약 + 규칙 기반 알림 + 최근 이벤트 50건."""

    @abstractmethod
    def events(
        self, kind: AccessEventKind | None, ip: str | None, hours: int, before_id: int | None, limit: int
    ) -> AccessEventPageDto:
        """최근 hours시간 이벤트를 종류·IP로 걸러 최신순 한 쪽. next_before_id로 다음 쪽을 잇는다."""
