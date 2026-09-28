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
    road_address: str | None = None
    jibun_address: str | None = None


@dataclass(frozen=True)
class IngestTarget:
    """수집 단위 = 인허가 슬러그 × 자치구 (인허가 API의 데이터셋 × OPN_ATMY_GRP_CD).

    industry_id는 앵커 업종 — 슬러그가 곧 업종인 기존 6종은 그대로 그 업종이고, 여러 업종을 담는
    슬러그(일반음식점)는 건별 업종을 분류기가 정한다. industry_ids는 그 슬러그가 낼 수 있는 업종
    전체(증분 커서용, 비어 있으면 앵커 하나), store_prefix는 store_id 접두(없으면 앵커 업종).
    """

    industry_id: str
    slug: str  # 인허가 API 업종슬러그 (예: karaoke_rooms)
    district_code: str
    authority_code: str  # 개방자치단체코드 (예: 3220000 강남구)
    industry_ids: tuple[str, ...] = ()
    store_prefix: str | None = None
