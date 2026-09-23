from pydantic import BaseModel


class HourGapBandResponse(BaseModel):
    """6구간 중 하나 — 두 강도 모두 시간당 보정값(1.0 = 24시간 균등), gap = sales − footfall."""

    hour_band: str  # 00_06 | 06_11 | 11_14 | 14_17 | 17_21 | 21_24
    footfall_intensity: float
    sales_intensity: float
    gap: float


class RegionIndustryHourGapResponse(BaseModel):
    """동×업종×분기 한 객체에 6구간 — 상세 계약 (`map-metric-contract` §3-2).

    `year_quarter`를 반드시 싣는다. 매출 원천은 20254까지라 프로필(20262)과 최신 분기가 다르다.
    화면은 두 선(유동·매출)을 그리고 gap 하나만 그리지 않는다 — 어긋남의 부호는 절대값이 아니라
    상대 위치에 있다(설계서 §6-2).
    """

    region_code: str
    industry_id: str
    year_quarter: str
    bands: list[HourGapBandResponse]
