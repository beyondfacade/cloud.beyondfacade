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
