from dataclasses import dataclass, field

from apps.shock.domain.entities.shock_event_entity import ShockEvent


@dataclass(frozen=True)
class LocatedEvent:
    """원천이 넘기는 지역 이벤트 1건 + 위치(WGS84). 좌표·지오코딩 실패면 lat/lng None."""

    event: ShockEvent
    lat: float | None
    lng: float | None


@dataclass
class RegionalIngestResult:
    """원천 1개 적재 결과 — 연결된 (이벤트, 행정동)과 건너뛴 이벤트를 사유별로."""

    linked: list[tuple[ShockEvent, str]] = field(default_factory=list)
    no_location: list[ShockEvent] = field(default_factory=list)  # 좌표 없음·지오코딩 실패
    no_region: list[ShockEvent] = field(default_factory=list)  # 좌표가 어느 행정동에도 안 듦
    inserted: int = 0
    updated: int = 0
