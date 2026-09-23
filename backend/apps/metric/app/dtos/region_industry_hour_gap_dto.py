from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass
class RegionIndustryHourGapDto:
    region_code: str
    industry_id: str
    year_quarter: str
    hour_band: str
    footfall_intensity: float
    sales_intensity: float
    gap: float


@dataclass(frozen=True)
class RegionHourValues:
    """행정동×분기의 시간대 6구간 유동인구 원값 (보정 전)."""

    region_code: str
    year_quarter: str
    values: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class RegionIndustryHourSales:
    """행정동×업종×분기의 시간대 6구간 매출 원값 (보정 전).

    여러 CS 코드가 한 업종에 붙는 경우(academy 4개·cafe 3개·hair_salon 3개)는 게이트웨이가
    **합산한 뒤** 넘긴다. 코드별로 강도를 내면 모집단이 쪼개진다 (설계서 §4-2).
    """

    region_code: str
    industry_id: str
    year_quarter: str
    values: Mapping[str, float] = field(default_factory=dict)
