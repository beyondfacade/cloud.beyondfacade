import logging
from collections.abc import Callable
from datetime import date, timedelta

from apps.shock.app.dtos.event_analog_dto import (
    AnalogCategoryDto,
    AnalogHintDto,
    CategoryOutlookDto,
    ConditionCompareDto,
    EventAnalogReportDto,
    EventImpactDto,
    IndustryRefDto,
    IndustrySeriesDto,
    NewsHeadlineDto,
    PeriodConditionDto,
    QuarterDto,
    RecentNewsDto,
)
from apps.shock.app.ports.input.event_analog_use_case import EventAnalogUseCase
from apps.shock.app.ports.output.event_analog_port import RecentNewsPort, StoreFlowPort
from apps.shock.app.ports.output.shock_event_port import ShockEventRepositoryPort
from apps.shock.domain.entities.shock_event_entity import ShockEvent
from apps.shock.domain.services.event_analog import (
    CategoryOutlook,
    EventImpact,
    QuarterImpact,
    category_outlook,
    event_impact,
    is_current,
    select_analogs,
    trend_counts,
    weak_streak,
)
from apps.shock.domain.services.event_category_hints import (
    HINT_KEYWORDS,
    MEASURE_KEYWORDS,
    categories_in,
)
from apps.shock.domain.services.event_window import add_months, month_of
from apps.shock.domain.services.industry_condition import PeriodCondition, condition_compare
from apps.shock.domain.services.industry_flows import IndustryFlows
from apps.shock.domain.services.recent_measures import HEADLINES_SHOWN, NEWS_DAYS, measure_headlines
from apps.shock.domain.value_objects.event_category import (
    CATEGORY_LABELS,
    CONDITION_COMPARED,
    EventCategory,
)

LOGGER = logging.getLogger("beyondfacade.shock.analogs")

_CAVEATS = [
    "서울 전체 인허가 기준이다 — 동·구는 점포가 적어 아무 일 없던 분기도 강세·약세로 자주 잡혀 쓰지 않는다. "
    "학원·어린이집·편의점·치킨·부동산중개는 흐름을 비교할 수 없어 뺐다.",
    "12월에는 행정 정리로 폐업이 몰린다 — 12월이 든 분기는 한 번씩 크게 튈 수 있어 판단은 분기 과반으로 한다.",
    "2020~2022년 폐업은 재난지원금·손실보상으로 지연되어 실제보다 적게 잡혔을 수 있다.",
    "변동폭은 이벤트 직전 1년의 같은 분기 대비다 — 비교 기간(최저임금·지원금 그 해 4분기, 감염병·근로시간 "
    "3년 12분기)에 겹친 다른 정책도 섞이므로 "
    "이벤트만의 효과로 단정하지 않는다.",
    "사례 직전과 최근 4분기 비교(condition)는 그 사이 몇 년의 다른 변화가 섞인 업종 상태 비교다 — 이벤트 효과로 "
    "읽지 않고, 과거 사례를 지금에 옮길 때 그때보다 약한지·강한지 가늠하는 데만 쓴다.",
]


def _month(day: date) -> str:
    return day.strftime("%Y-%m")


def _quarter(impact: QuarterImpact, event: ShockEvent, others: list[ShockEvent]) -> QuarterDto:
    quarter = impact.quarter
    window = quarter.window
    return QuarterDto(
        quarter=quarter.index + 1,
        label=f"{quarter.year}년 차 {quarter.number}분기",
        start_month=_month(window.start),
        end_month=_month(add_months(window.end, -1)),
        overlaps=[
            e.name
            for e in others
            if e.event_id != event.event_id and window.start <= month_of(e.start_date) < window.end
        ],
    )


def _series(
    impact: EventImpact,
    target_id: str,
    outlook: CategoryOutlook | None,
    names: dict[str, str],
) -> list[IndustrySeriesDto]:
    roles = [(target_id, "target")]
    if outlook:
        roles += [(i, "recommended") for i, _ in outlook.recommended]
        roles += [(i, "avoid") for i, _ in outlook.avoid]
    return [
        IndustrySeriesDto(industry_id, names.get(industry_id, industry_id), role, impact.series(industry_id))
        for industry_id, role in roles
    ]


def _outlook(outlook: CategoryOutlook, condition: ConditionCompareDto | None) -> CategoryOutlookDto:
    return CategoryOutlookDto(
        category=outlook.category,
        label=CATEGORY_LABELS[outlook.category],
        analog_count=outlook.analog_count,
        target_trend=outlook.target_trend,
        recommended=[IndustryRefDto(i, name) for i, name in outlook.recommended],
        avoid=[IndustryRefDto(i, name) for i, name in outlook.avoid],
        typical_duration_months=outlook.typical_duration_months,
        condition=condition,
    )


def _period(condition: PeriodCondition) -> PeriodConditionDto:
    return PeriodConditionDto(
        start_month=_month(condition.window.start),
        end_month=_month(add_months(condition.window.end, -1)),
        growth_pct=condition.growth_pct,
        all_growth_pct=condition.all_growth_pct,
        excess_pct=condition.excess_pct,
        closure_rate_pct=condition.closure_rate_pct,
        rank=condition.rank,
        industry_count=condition.industry_count,
    )


def _condition(
    category: str, impacts: list[EventImpact], flows: list[IndustryFlows], target_id: str, today: date
) -> ConditionCompareDto | None:
    """드문 유형만 — 가장 최근 사례(유형 안에서 최근순으로 골라 뒀다)의 직전과 지금을 견준다."""
    if category not in CONDITION_COMPARED:
        return None
    latest = next((i.event for i in impacts if i.event.category == category), None)
    compare = latest and condition_compare(flows, target_id, latest.start_date, today)
    if not compare:
        return None
    return ConditionCompareDto(
        event_id=latest.event_id,
        event_name=latest.name,
        direction=compare.direction,
        before=_period(compare.before),
        recent=_period(compare.recent),
    )


def _hints(compared: set[str]) -> list[AnalogHintDto]:
    return [
        AnalogHintDto(category, CATEGORY_LABELS[category], keyword)
        for category, keyword in HINT_KEYWORDS.items()
        if category not in compared
    ]


class EventAnalogInteractor(EventAnalogUseCase):
    def __init__(
        self,
        events: ShockEventRepositoryPort,
        flows: StoreFlowPort,
        today: Callable[[], date] = date.today,
        news: RecentNewsPort | None = None,
    ) -> None:
        self._events = events
        self._flows = flows
        self._today = today
        self._news = news

    def _recent_news(self, category: AnalogCategoryDto, today: date) -> RecentNewsDto:
        """뉴스 검색이 실패해도 유사 사례는 나간다 — 확인하지 못했다고만 싣는다."""
        keywords = MEASURE_KEYWORDS[EventCategory(category.category)]
        base = RecentNewsDto(category.category, category.label, NEWS_DAYS, list(keywords), checked=False)
        try:
            found = [h for keyword in keywords for h in self._news.latest(keyword)]
        except Exception:
            LOGGER.warning("최근 조치 기사 검색 실패 — %s", category.category, exc_info=True)
            return base
        picked = measure_headlines(found, keywords, today - timedelta(days=NEWS_DAYS))
        base.checked = True
        base.article_count = len(picked)
        base.headlines = [
            NewsHeadlineDto(h.title, h.published_at.date().isoformat(), h.url) for h in picked[:HEADLINES_SHOWN]
        ]
        return base

    def analogs(self, industry_id: str, question: str | None) -> EventAnalogReportDto:
        today = self._today()
        events = self._events.list_categorized()
        current = [e for e in events if is_current(e, today)]
        categories = [AnalogCategoryDto(c, CATEGORY_LABELS[c], "question") for c in categories_in(question)]
        for event in current:
            if all(c.category != event.category for c in categories):
                categories.append(AnalogCategoryDto(event.category, CATEGORY_LABELS[event.category], "current"))
        analogs = select_analogs(events, [c.category for c in categories], today)
        # 진행 중으로 등록된 이벤트가 없는 질문 속 유형은 지금 그 상황인지 뉴스로 확인한다
        running = {e.category for e in current}
        unconfirmed = [c for c in categories if c.reason == "question" and c.category not in running]
        flows = self._flows.monthly_flows() if current or analogs else []
        names = {f.industry_id: f.industry_name for f in flows}

        def impacts(chosen: list[ShockEvent]) -> list[EventImpact]:
            return [event_impact(e, flows, industry_id, today) for e in chosen]

        analog_impacts = impacts(analogs)
        outlooks = {
            c.category: category_outlook(
                c.category, [i for i in analog_impacts if i.event.category == c.category], industry_id
            )
            for c in categories
            if any(i.event.category == c.category for i in analog_impacts)
        }

        def to_dto(impact: EventImpact) -> EventImpactDto:
            event = impact.event
            target_values = impact.series(industry_id)
            weak, strong = trend_counts(target_values)
            return EventImpactDto(
                event_id=event.event_id,
                name=event.name,
                category=event.category or "",
                category_label=CATEGORY_LABELS.get(event.category or "", ""),
                start_date=event.start_date,
                end_date=event.end_date,
                duration_months=impact.duration_months,
                description=event.description,
                source=event.source,
                current=impact.current,
                years=impact.years,
                quarters=[_quarter(q, event, events) for q in impact.quarters],
                series=_series(impact, industry_id, outlooks.get(event.category or ""), names),
                target_weak_quarters=weak,
                target_strong_quarters=strong,
                target_weak_streak=weak_streak(target_values),
            )

        return EventAnalogReportDto(
            industry_id=industry_id,
            as_of=_month(add_months(month_of(today), -1)),
            categories=categories,
            current_events=[to_dto(i) for i in impacts(current)],
            analogs=[to_dto(i) for i in analog_impacts],
            outlooks=[_outlook(o, _condition(o.category, analog_impacts, flows, industry_id, today)) for o in outlooks.values()],
            caveats=list(_CAVEATS),
            hints=_hints({c.category for c in categories}),
            recent_news=[self._recent_news(c, today) for c in unconfirmed] if self._news else [],
        )
