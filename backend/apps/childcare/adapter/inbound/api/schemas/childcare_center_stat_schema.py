from datetime import date

from pydantic import BaseModel


class ChildcareRegionSummaryResponse(BaseModel):
    """행정동 어린이집 요약 (프론트엔드 사이드패널 계약)."""

    region_code: str
    base_date: date | None
    center_count: int
    capacity: int
    child_count: int
    occupancy_rate: float | None
    waiting_count: int | None
