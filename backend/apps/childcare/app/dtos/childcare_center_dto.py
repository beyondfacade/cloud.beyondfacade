from dataclasses import dataclass
from datetime import date


@dataclass
class ChildcareCenterDto:
    """지도 마커 단위 — 시설 + 최신 현황 평탄화."""

    center_id: str
    name: str
    type_name: str
    status_name: str | None
    lat: float
    lng: float
    base_date: date
    capacity: int
    child_count: int
    waiting_count: int | None
