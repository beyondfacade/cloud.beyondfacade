"""유사 사례 — 이벤트마다 분기별 업종 변동폭을 모으고, 같은 유형의 지난 이벤트를 고른다.

강세·약세 업종은 **평소 대비** 점포수 증감(excess_pct)으로 줄 세운다 — 원래 늘던 업종이
그대로 는 것은 이벤트의 영향이 아니다. 한 분기만 튀는 값(연말 행정 정리 등)에 휘둘리지 않게
판단은 분기 과반으로 한다.
"""

from dataclasses import dataclass
from datetime import date
from statistics import fmean, median

from apps.shock.domain.entities.shock_event_entity import ShockEvent
from apps.shock.domain.services.event_window import (
    Quarter,
    add_months,
    event_quarters,
    month_of,
    months_between,
)
from apps.shock.domain.services.industry_flows import IndustryFlows, WindowChange
from apps.shock.domain.value_objects.event_category import CATEGORY_YEARS

TOP_MOVERS = 3
ANALOGS_PER_CATEGORY = 3
# 점포가 이보다 적은 업종은 몇 곳의 개폐업으로 증감률이 크게 흔들려 순위에서 뺀다
MIN_STOCK = 100
# 평소 대비 ±0.3%p 안은 강세도 약세도 아닌 '평소와 비슷'으로 센다
TREND_BAND = 0.3


@dataclass(frozen=True)
class IndustryMove:
    industry_id: str
    industry_name: str
    change: WindowChange


@dataclass(frozen=True)
class QuarterImpact:
    quarter: Quarter
    target: IndustryMove | None
    strongest: list[IndustryMove]
    weakest: list[IndustryMove]
    excess: dict[str, float | None]  # 업종 ID → 평소 대비 증감(%p) — 업종별 분기 흐름용


@dataclass(frozen=True)
class EventImpact:
    event: ShockEvent
    current: bool
    years: int  # 유형의 비교 기간
    duration_months: int | None  # 끝나지 않은 이벤트는 None
    quarters: list[QuarterImpact]

    def series(self, industry_id: str) -> list[float | None]:
        return [q.excess.get(industry_id) for q in self.quarters]


@dataclass(frozen=True)
class CategoryOutlook:
    """같은 유형 지난 사례들의 결론 — 리포트가 '앞으로 예상되는 흐름'을 이 값으로 쓴다."""

    category: str
    analog_count: int
    target_trend: str  # weak / strong / mixed / unknown
    recommended: list[tuple[str, str]]  # (업종 ID, 이름) — 사례 분기에서 반복해 강세
    avoid: list[tuple[str, str]]  # 반복해 약세
    typical_duration_months: int | None


def trend_counts(values: list[float | None]) -> tuple[int, int]:
    """(약세 분기 수, 강세 분기 수)."""
    known = [v for v in values if v is not None]
    return (
        sum(1 for v in known if v <= -TREND_BAND),
        sum(1 for v in known if v >= TREND_BAND),
    )


def weak_streak(values: list[float | None]) -> int:
    """첫 분기부터 끊기지 않고 약세였던 분기 수 — '약세가 얼마나 이어졌나'."""
    streak = 0
    for value in values:
        if value is None or value > -TREND_BAND:
            break
        streak += 1
    return streak


def _trend(values: list[float]) -> str:
    if not values:
        return "unknown"
    weak, strong = trend_counts(values)
    if weak * 2 > len(values):
        return "weak"
    if strong * 2 > len(values):
        return "strong"
    return "mixed"


def _tally(quarters: list[QuarterImpact], exclude: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """강세 분기 +1, 약세 분기 −1로 센 순점수 — 양수는 추천, 음수는 피할 업종.

    강세와 약세를 오간 업종(순점수 0)은 어느 쪽에도 넣지 않는다. 같은 점수면 평균 변동폭으로 가른다.
    """
    net: dict[str, int] = {}
    values: dict[str, list[float]] = {}
    names: dict[str, str] = {}
    for quarter in quarters:
        for point, moves in ((1, quarter.strongest), (-1, quarter.weakest)):
            for move in moves:
                if move.industry_id == exclude or move.change.excess_pct is None:
                    continue
                net[move.industry_id] = net.get(move.industry_id, 0) + point
                values.setdefault(move.industry_id, []).append(move.change.excess_pct)
                names[move.industry_id] = move.industry_name
    up = sorted((i for i in net if net[i] > 0), key=lambda i: (-net[i], -fmean(values[i])))
    down = sorted((i for i in net if net[i] < 0), key=lambda i: (net[i], fmean(values[i])))
    return (
        [(i, names[i]) for i in up[:TOP_MOVERS]],
        [(i, names[i]) for i in down[:TOP_MOVERS]],
    )


def category_outlook(category: str, impacts: list[EventImpact], target_id: str) -> CategoryOutlook:
    quarters = [q for impact in impacts for q in impact.quarters]
    durations = [i.duration_months for i in impacts if i.duration_months is not None]
    recommended, avoid = _tally(quarters, target_id)
    return CategoryOutlook(
        category=category,
        analog_count=len(impacts),
        target_trend=_trend(
            [q.target.change.excess_pct for q in quarters if q.target and q.target.change.excess_pct is not None]
        ),
        recommended=recommended,
        avoid=avoid,
        typical_duration_months=round(median(durations)) if durations else None,
    )


def is_current(event: ShockEvent, today: date) -> bool:
    """유형이 있고, 유형의 비교 기간 안에 시작해 아직 끝나지 않은 이벤트."""
    if event.category is None or event.start_date > today:
        return False
    if event.end_date is not None and event.end_date < today:
        return False
    return add_months(month_of(event.start_date), 12 * CATEGORY_YEARS[event.category]) > month_of(today)


def quarter_impact(quarter: Quarter, flows: list[IndustryFlows], target_id: str) -> QuarterImpact:
    moves = {
        f.industry_id: IndustryMove(f.industry_id, f.industry_name, f.change(quarter.window, quarter.baseline))
        for f in flows
    }
    ranked = sorted(
        (
            moves[f.industry_id]
            for f in flows
            if moves[f.industry_id].change.excess_pct is not None
            and f.stock_at(quarter.window.start) >= MIN_STOCK
        ),
        key=lambda move: move.change.excess_pct,
        reverse=True,
    )
    strongest = ranked[:TOP_MOVERS]
    rest = ranked[len(strongest) :]
    return QuarterImpact(
        quarter=quarter,
        target=moves.get(target_id),
        strongest=strongest,
        weakest=rest[::-1][:TOP_MOVERS],
        excess={i: move.change.excess_pct for i, move in moves.items()},
    )


def event_impact(
    event: ShockEvent,
    flows: list[IndustryFlows],
    target_id: str,
    today: date,
) -> EventImpact:
    years = CATEGORY_YEARS[event.category] if event.category else 1
    return EventImpact(
        event=event,
        current=is_current(event, today),
        years=years,
        duration_months=None
        if event.end_date is None
        else months_between(event.start_date, event.end_date),
        quarters=[
            quarter_impact(quarter, flows, target_id)
            for quarter in event_quarters(event.start_date, today, years)
        ],
    )


def select_analogs(
    events: list[ShockEvent], categories: list[str], today: date
) -> list[ShockEvent]:
    """요청 유형 순서대로, 유형마다 진행 중이 아닌 지난 이벤트를 최근순으로 최대 3건."""
    picked: list[ShockEvent] = []
    for category in categories:
        past = sorted(
            (
                e
                for e in events
                if e.category == category and e.start_date <= today and not is_current(e, today)
            ),
            key=lambda e: e.start_date,
            reverse=True,
        )
        picked.extend(past[:ANALOGS_PER_CATEGORY])
    return picked
