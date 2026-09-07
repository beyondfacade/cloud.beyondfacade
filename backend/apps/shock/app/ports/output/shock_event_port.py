"""Driven Ports — shock_event가 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.shock.domain.entities.shock_event_entity import ShockEvent


class ShockEventRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, events: list[ShockEvent]) -> tuple[int, int]:
        """event_id 기준 업서트(멱등, 업종 영향 행 교체 포함) — (신규, 갱신) 반환."""

    @abstractmethod
    def list_events(self, industry_id: str | None, limit: int) -> list[ShockEvent]:
        """시행일 오름차순 limit건 — industry_id가 있으면 영향 업종으로 필터."""


class ShockEventSourcePort(ABC):
    """충격 원천 — 거리두기 API·시드 파일 등 어떤 소스든 같은 계약으로 들어온다."""

    @abstractmethod
    def fetch_events(self) -> list[ShockEvent]:
        """원천에서 충격 목록을 수신해 엔티티로 반환한다."""
