from datetime import date, datetime

from pydantic import BaseModel


class StoreResponse(BaseModel):
    store_id: str
    name: str
    industry_id: str
    district_code: str
    open_date: date | None
    close_date: date | None
    status_code: str
    status_name: str
    lat: float | None
    lng: float | None
    source_updated_at: datetime
    region_code: str | None = None
    subcategory_id: str | None = None


class StoreMarkerResponse(BaseModel):
    """지도 마커 응답 단위 (프론트엔드 계약) — 좌표 보유 영업 점포만."""

    store_id: str
    name: str
    lat: float
    lng: float
    status_name: str
    open_date: date | None
