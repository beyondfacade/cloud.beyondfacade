"""Driven Ports — ④지역 이벤트(shock_event_region)가 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.shock.app.dtos.shock_event_region_dto import LocatedEvent
from apps.shock.domain.entities.shock_event_entity import ShockEvent


class ShockEventRegionRepositoryPort(ABC):
    @abstractmethod
    def replace_links(self, links: list[tuple[str, str]]) -> int:
        """(event_id, region_code) — 해당 이벤트의 기존 연결을 지우고 다시 쓴다(멱등). 연결 수 반환."""

    @abstractmethod
    def list_by_region(self, region_code: str) -> list[ShockEvent]:
        """행정동 1곳에 연결된 이벤트 — 시작일 내림차순(최근 것 먼저)."""


class RegionalEventSourcePort(ABC):
    """지역 이벤트 원천 — 정비사업·대규모점포·아파트 어느 것이든 같은 계약으로 들어온다."""

    @abstractmethod
    def fetch_located_events(self) -> list[LocatedEvent]:
        """원천을 수신해 이벤트와 위치를 함께 반환한다."""


class RegionLocatorPort(ABC):
    @abstractmethod
    def locate(self, lat: float, lng: float) -> str | None:
        """WGS84 점 → 행정동 region_code. 어느 경계에도 안 들면 None."""
