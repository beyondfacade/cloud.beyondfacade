from datetime import date

from pydantic import BaseModel


class QuarterResponse(BaseModel):
    quarter: int
    label: str
    start_month: str
    end_month: str
    overlaps: list[str] = []


class IndustrySeriesResponse(BaseModel):
    industry_id: str
    industry_name: str
    role: str
    values: list[float | None] = []


class EventImpactResponse(BaseModel):
    event_id: str
    name: str
    category: str
    category_label: str
    start_date: date
    end_date: date | None
    duration_months: int | None
    description: str | None
    source: str
    current: bool
    quarters: list[QuarterResponse] = []
    series: list[IndustrySeriesResponse] = []
    target_weak_quarters: int = 0
    target_strong_quarters: int = 0
    target_weak_streak: int = 0


class AnalogCategoryResponse(BaseModel):
    category: str
    label: str
    reason: str


class IndustryRefResponse(BaseModel):
    industry_id: str
    industry_name: str


class CategoryOutlookResponse(BaseModel):
    category: str
    label: str
    analog_count: int
    target_trend: str
    recommended: list[IndustryRefResponse] = []
    avoid: list[IndustryRefResponse] = []
    typical_duration_months: int | None = None


class EventAnalogReportResponse(BaseModel):
    industry_id: str
    years: int
    as_of: str
    categories: list[AnalogCategoryResponse] = []
    current_events: list[EventImpactResponse] = []
    analogs: list[EventImpactResponse] = []
    outlooks: list[CategoryOutlookResponse] = []
    caveats: list[str] = []
