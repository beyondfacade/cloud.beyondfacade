"""Driving Port — ④지역 이벤트(shock_event_region) UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.shock.app.dtos.shock_event_dto import ShockEventDto
from apps.shock.app.dtos.shock_event_region_dto import RegionalIngestResult
from apps.shock.app.ports.output.shock_event_region_port import RegionalEventSourcePort


class ShockEventRegionUseCase(ABC):
    @abstractmethod
    def ingest(self, source: RegionalEventSourcePort) -> RegionalIngestResult:
        """원천 1개 수신 → 행정동 판정 → shock_event 업서트 + 행정동 연결(멱등). 판정 실패는 건너뛰고 센다."""

    @abstractmethod
    def list_for_region(self, region_code: str) -> list[ShockEventDto]:
        """행정동 1곳의 지역 이벤트 — 시작일 내림차순."""
