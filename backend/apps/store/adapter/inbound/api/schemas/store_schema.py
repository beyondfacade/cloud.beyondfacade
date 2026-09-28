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
    road_address: str | None = None
    jibun_address: str | None = None


class StoreMarkerResponse(BaseModel):
    """좌표 보유 점포. status=open은 영업 중(close_date null), closed는 최근 2년 폐업."""

    store_id: str
    name: str
    lat: float
    lng: float
    status_name: str
    open_date: date | None
    close_date: date | None = None
