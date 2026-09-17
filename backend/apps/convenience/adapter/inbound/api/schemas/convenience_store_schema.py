from pydantic import BaseModel


class ConvenienceStoreMarkerResponse(BaseModel):
    """지도 마커 응답 단위 (프론트엔드 계약) — 좌표 보유 현행 편의점."""

    store_id: str
    name: str
    branch_name: str | None
    brand: str | None
    lat: float
    lng: float
    road_address: str | None


class BrandCountResponse(BaseModel):
    brand: str | None  # None = 미확인(기타) 브랜드
    count: int


class ConvenienceRegionSummaryResponse(BaseModel):
    """행정동 편의점 요약 (프론트엔드 사이드패널 계약)."""

    region_code: str
    store_count: int
    brands: list[BrandCountResponse]
    source_stdr_ym: str | None
