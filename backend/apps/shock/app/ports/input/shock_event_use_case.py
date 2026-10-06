"""Driving Port — shock_event UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.shock.app.dtos.shock_event_dto import ShockEventDto
from apps.shock.domain.entities.shock_event_entity import ShockEvent


class ShockEventUseCase(ABC):
    @abstractmethod
    def ingest(self) -> tuple[int, int]:
        """소스(거리두기 API 또는 시드 파일)에서 수신·업서트(멱등) — (신규, 갱신) 반환."""

    @abstractmethod
    def list_events(self, industry_id: str | None, limit: int) -> list[ShockEventDto]:
        """충격 목록 — 업종 필터 선택, 시행일 오름차순(타임라인)."""

    @abstractmethod
    def register(self, event: ShockEvent) -> tuple[int, int]:
        """운영자가 이벤트 1건을 등록·수정한다(지금 진행 중인 이벤트를 유형과 함께) — (신규, 갱신)."""
