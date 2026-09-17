from dataclasses import dataclass


@dataclass
class ConvenienceStoreDto:
    """지도 마커 단위 — 좌표 보유 현행 편의점."""

    store_id: str
    name: str
    branch_name: str | None
    brand: str | None
    lat: float
    lng: float
    road_address: str | None


@dataclass
class BrandCountDto:
    brand: str | None
    count: int


@dataclass
class ConvenienceRegionSummaryDto:
    region_code: str
    store_count: int
    brands: list[BrandCountDto]
    source_stdr_ym: str | None
