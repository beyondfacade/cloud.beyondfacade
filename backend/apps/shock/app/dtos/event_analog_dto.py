from dataclasses import dataclass, field
from datetime import date


@dataclass
class QuarterDto:
    quarter: int  # 이벤트 기준 1부터
    label: str  # "1년 차 1분기" 등
    start_month: str  # YYYY-MM
    end_month: str  # YYYY-MM (포함)
    overlaps: list[str] = field(default_factory=list)  # 이 분기에 시작한 다른 유형 이벤트 이름


@dataclass
class IndustrySeriesDto:
    industry_id: str
    industry_name: str
    role: str  # target: 내 업종 / recommended: 사례에서 거듭 강세 / avoid: 거듭 약세
    values: list[float | None] = field(default_factory=list)  # 분기별 평소 대비 점포수 증감(%p)


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
    quarters: list[QuarterDto] = field(default_factory=list)
    series: list[IndustrySeriesDto] = field(default_factory=list)
    target_weak_quarters: int = 0  # 내 업종이 평소보다 0.3%p 넘게 줄어든 분기 수 (흩어진 것 포함)
    target_strong_quarters: int = 0
    target_weak_streak: int = 0  # 1분기부터 끊기지 않고 약세였던 분기 수


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
    target_trend: str  # weak / strong / mixed / unknown — 대상 업종이 지난 사례 분기 과반에서 어땠나
    recommended: list[IndustryRefDto] = field(default_factory=list)
    avoid: list[IndustryRefDto] = field(default_factory=list)
    typical_duration_months: int | None = None


@dataclass
class EventAnalogReportDto:
    industry_id: str
    years: int
    as_of: str  # 마지막 완결 달 YYYY-MM
    categories: list[AnalogCategoryDto] = field(default_factory=list)
    current_events: list[EventImpactDto] = field(default_factory=list)
    analogs: list[EventImpactDto] = field(default_factory=list)
    outlooks: list[CategoryOutlookDto] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
