from datetime import date

from pydantic import BaseModel


class ChildcareCenterMarkerResponse(BaseModel):
    """지도 마커 응답 단위 (프론트엔드 계약) — 운영 중·좌표 보유 시설 + 최신 현황."""

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
