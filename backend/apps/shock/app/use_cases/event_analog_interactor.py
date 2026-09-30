from collections.abc import Callable
from datetime import date

from apps.shock.app.dtos.event_analog_dto import (
    AnalogCategoryDto,
    CategoryOutlookDto,
    EventAnalogReportDto,
    EventImpactDto,
    IndustryRefDto,
    IndustrySeriesDto,
    QuarterDto,
)
from apps.shock.app.ports.input.event_analog_use_case import EventAnalogUseCase
from apps.shock.app.ports.output.event_analog_port import StoreFlowPort
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
from apps.shock.domain.services.event_category_hints import categories_in
from apps.shock.domain.services.event_window import add_months, month_of
from apps.shock.domain.value_objects.event_category import CATEGORY_LABELS, EventCategory

_CAVEATS = [
    "서울 전체 인허가 기준이다 — 학원·어린이집·편의점·치킨·부동산중개는 흐름을 비교할 수 없어 뺐다.",
    "12월에는 행정 정리로 폐업이 몰린다 — 12월이 든 분기는 한 번씩 크게 튈 수 있어 판단은 분기 과반으로 한다.",
    "2020~2022년 폐업은 재난지원금·손실보상으로 지연되어 실제보다 적게 잡혔을 수 있다.",
    "변동폭은 이벤트 직전 1년의 같은 분기 대비다 — 비교 기간(최저임금·지원금 그 해 4분기, 감염병·근로시간 "
    "3년 12분기)에 겹친 다른 정책도 섞이므로 "
    "이벤트만의 효과로 단정하지 않는다.",
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


def _outlook(outlook: CategoryOutlook) -> CategoryOutlookDto:
    return CategoryOutlookDto(
        category=outlook.category,
        label=CATEGORY_LABELS[outlook.category],
        analog_count=outlook.analog_count,
        target_trend=outlook.target_trend,
        recommended=[IndustryRefDto(i, name) for i, name in outlook.recommended],
        avoid=[IndustryRefDto(i, name) for i, name in outlook.avoid],
        typical_duration_months=outlook.typical_duration_months,
    )


class EventAnalogInteractor(EventAnalogUseCase):
    def __init__(
        self,
        events: ShockEventRepositoryPort,
        flows: StoreFlowPort,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._events = events
        self._flows = flows
        self._today = today

    def myself(self) -> EventAnalogReportDto:
        return EventAnalogReportDto(
            industry_id="myself",
            as_of="2026-08",
            categories=[AnalogCategoryDto(EventCategory.PANDEMIC, CATEGORY_LABELS[EventCategory.PANDEMIC], "question")],
            analogs=[
                EventImpactDto(
                    event_id="myself",
                    name="shock 유사 사례 배선 검증",
                    category=EventCategory.PANDEMIC,
                    category_label=CATEGORY_LABELS[EventCategory.PANDEMIC],
                    start_date=date(2020, 1, 20),
                    end_date=None,
                    duration_months=None,
                    description=None,
                    source="beyondfacade",
                    current=False,
                    years=3,
                    quarters=[QuarterDto(1, "1년 차 1분기", "2020-01", "2020-03")],
                    series=[IndustrySeriesDto("myself", "배선 검증", "target", [None])],
                )
            ],
        )

    def analogs(self, industry_id: str, question: str | None) -> EventAnalogReportDto:
        today = self._today()
        events = self._events.list_categorized()
        current = [e for e in events if is_current(e, today)]
        categories = [AnalogCategoryDto(c, CATEGORY_LABELS[c], "question") for c in categories_in(question)]
        for event in current:
            if all(c.category != event.category for c in categories):
                categories.append(AnalogCategoryDto(event.category, CATEGORY_LABELS[event.category], "current"))
        analogs = select_analogs(events, [c.category for c in categories], today)
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
            outlooks=[_outlook(o) for o in outlooks.values()],
            caveats=list(_CAVEATS),
        )
