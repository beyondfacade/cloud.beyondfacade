from pydantic import BaseModel


class RegionIndustryMetricResponse(BaseModel):
    region_code: str
    industry_id: str
    year: int
    store_count: int
    open_count: int
    close_count: int
    closure_rate: float | None
    growth_rate: float | None


class MetricValueResponse(BaseModel):
    """단계구분도 응답 단위 — {region_code, value} (프론트엔드 계약)."""

    region_code: str
    value: float
