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
    years: int  # 유형의 비교 기간 — 최저임금·지원금 1년(4분기), 감염병·근로시간 3년(12분기)
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
class AnalogHintDto:
    category: str
    label: str
    keyword: str  # 질문에 넣으면 이 유형도 비교하는 대표 단서


@dataclass
class NewsHeadlineDto:
    title: str
    published_at: str  # YYYY-MM-DD
    url: str


@dataclass
class RecentNewsDto:
    """진행 중 이벤트가 없는 질문 속 유형 — 지금 그 상황인지 최근 조치 기사로 확인한 결과."""

    category: str
    label: str
    days: int
    keywords: list[str]
    checked: bool  # False: 검색 실패로 확인하지 못함
    article_count: int = 0  # 기간 안에 제목에 조치 단어가 든 기사 수
    headlines: list[NewsHeadlineDto] = field(default_factory=list)  # 최신 몇 건


@dataclass
class IndustryRefDto:
    industry_id: str
    industry_name: str


@dataclass
class PeriodConditionDto:
    start_month: str  # YYYY-MM
    end_month: str  # YYYY-MM (포함)
    growth_pct: float  # 대상 업종 점포수 증감률
    all_growth_pct: float  # 전 업종 합계 점포수 증감률
    excess_pct: float  # 대상 − 전 업종 (%p)
    closure_rate_pct: float
    rank: int
    industry_count: int


@dataclass
class ConditionCompareDto:
    """가장 최근 사례 직전 4분기 vs 최근 4분기 — 과거 사례를 지금에 옮길 때의 보정 근거 (이벤트 효과 아님)."""

    event_id: str
    event_name: str
    direction: str  # weaker: 그때보다 약한 상태 / stronger: 강한 상태 / similar
    before: PeriodConditionDto
    recent: PeriodConditionDto


@dataclass
class CategoryOutlookDto:
    category: str
    label: str
    analog_count: int
    target_trend: str  # weak / strong / mixed / unknown — 대상 업종이 지난 사례 분기 과반에서 어땠나
    recommended: list[IndustryRefDto] = field(default_factory=list)
    avoid: list[IndustryRefDto] = field(default_factory=list)
    typical_duration_months: int | None = None
    condition: ConditionCompareDto | None = None


@dataclass
class EventAnalogReportDto:
    industry_id: str
    as_of: str  # 마지막 완결 달 YYYY-MM
    categories: list[AnalogCategoryDto] = field(default_factory=list)
    current_events: list[EventImpactDto] = field(default_factory=list)
    analogs: list[EventImpactDto] = field(default_factory=list)
    outlooks: list[CategoryOutlookDto] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    hints: list[AnalogHintDto] = field(default_factory=list)  # 이번에 비교하지 않은 유형 — 화면 안내용
    recent_news: list[RecentNewsDto] = field(default_factory=list)
