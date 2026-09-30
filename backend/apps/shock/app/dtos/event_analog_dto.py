from dataclasses import dataclass, field
from datetime import date


@dataclass
class IndustryMoveDto:
    industry_id: str
    industry_name: str
    openings: int
    closings: int
    openings_yoy_pct: float | None
    closings_yoy_pct: float | None
    stock_change_pct: float | None
    excess_pct: float | None


@dataclass
class WindowImpactDto:
    kind: str  # immediate / late / recent
    label: str  # "직후 3개월" 등
    start_month: str  # YYYY-MM
    end_month: str  # YYYY-MM (포함)
    target: IndustryMoveDto | None
    strongest: list[IndustryMoveDto] = field(default_factory=list)
    weakest: list[IndustryMoveDto] = field(default_factory=list)


@dataclass
class EventImpactDto:
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
    windows: list[WindowImpactDto] = field(default_factory=list)


@dataclass
class AnalogCategoryDto:
    category: str
    label: str
    reason: str  # question: 질문 속 단서 / current: 진행 중 등록 이벤트


@dataclass
class IndustryRefDto:
    industry_id: str
    industry_name: str


@dataclass
class CategoryOutlookDto:
    category: str
    label: str
    analog_count: int
    target_trend: str  # weak / strong / mixed / unknown — 대상 업종이 지난 사례에서 어땠나
    recommended: list[IndustryRefDto] = field(default_factory=list)
    avoid: list[IndustryRefDto] = field(default_factory=list)
    typical_duration_months: int | None = None


@dataclass
class EventAnalogReportDto:
    industry_id: str
    months: int
    years: int
    as_of: str  # 마지막 완결 달 YYYY-MM
    categories: list[AnalogCategoryDto] = field(default_factory=list)
    current_events: list[EventImpactDto] = field(default_factory=list)
    analogs: list[EventImpactDto] = field(default_factory=list)
    outlooks: list[CategoryOutlookDto] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
