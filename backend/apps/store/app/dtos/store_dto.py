from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class StoreDto:
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


@dataclass(frozen=True)
class IngestTarget:
    """수집 단위 = 업종 × 자치구 (인허가 API의 데이터셋 × OPN_ATMY_GRP_CD)."""

    industry_id: str
    slug: str  # 인허가 API 업종슬러그 (예: karaoke_rooms)
    district_code: str
    authority_code: str  # 개방자치단체코드 (예: 3220000 강남구)
