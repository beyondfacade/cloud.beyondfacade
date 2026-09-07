from dataclasses import dataclass


@dataclass
class RegionIndustryMetric:
    """행정동×업종×연도 집계 지표 — store 원천에서 배치 재생성 (집계 계층, docs/erd.md)."""

    region_code: str
    industry_id: str
    year: int
    store_count: int  # 해당 연도 말(12-31) 기준 영업 중 점포 수
    open_count: int  # 당해 개업 수
    close_count: int  # 당해 폐업 수
    closure_rate: float | None  # close_count ÷ 전년 말 store_count (전년 0이면 None)
    growth_rate: float | None  # (open_count − close_count) ÷ 전년 말 store_count (전년 0이면 None)
