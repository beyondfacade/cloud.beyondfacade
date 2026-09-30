from datetime import date

from pydantic import BaseModel


class IndustryMoveResponse(BaseModel):
    industry_id: str
    industry_name: str
    openings: int
    closings: int
    openings_yoy_pct: float | None
    closings_yoy_pct: float | None
    stock_change_pct: float | None
    excess_pct: float | None


class WindowImpactResponse(BaseModel):
    kind: str
    label: str
    start_month: str
    end_month: str
    target: IndustryMoveResponse | None
    strongest: list[IndustryMoveResponse] = []
    weakest: list[IndustryMoveResponse] = []


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
    windows: list[WindowImpactResponse] = []


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
    months: int
    years: int
    as_of: str
    categories: list[AnalogCategoryResponse] = []
    current_events: list[EventImpactResponse] = []
    analogs: list[EventImpactResponse] = []
    outlooks: list[CategoryOutlookResponse] = []
    caveats: list[str] = []
