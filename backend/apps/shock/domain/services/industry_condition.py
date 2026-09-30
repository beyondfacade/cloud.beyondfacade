"""직전·최근 업종 상태 — 과거 사례를 지금에 얼마나 그대로 옮길 수 있나 가늠하는 보정 근거.

유사 사례는 "비슷한 충격이 오면 그때처럼 움직인다"를 가정한다. 그런데 이벤트 직전 업종이 한창 늘던
중이었는지, 지금처럼 폐업이 개업을 앞지르는 중인지에 따라 같은 충격도 다르게 닿는다.
두 창 사이 몇 년의 다른 변화(프랜차이즈 확산·최저임금 누적·금리)가 섞이므로 이벤트 효과가 아니다.
업종 고유의 변화만 보려고 전 업종 증감률을 뺀 값(`excess_pct`)으로 견준다.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

from apps.shock.domain.services.event_window import Window, add_months, month_of
from apps.shock.domain.services.industry_flows import IndustryFlows

CONDITION_MONTHS = 12  # 4분기 — 계절·12월 행정 정리가 두 창에 똑같이 든다
STEADY_BAND = 1.0  # 전 업종 대비 차이가 이만큼(%p) 안에서 움직이면 비슷한 상태로 본다

Direction = Literal["weaker", "stronger", "similar"]


@dataclass(frozen=True)
class PeriodCondition:
    window: Window
    growth_pct: float  # 대상 업종 점포수 증감률
    all_growth_pct: float  # 비교 가능한 전 업종 합계 점포수 증감률
    excess_pct: float  # 대상 − 전 업종 (%p)
    closure_rate_pct: float  # 창 동안 폐업 수 / 창 시작 점포수
    rank: int  # 증감률 순위 (1 = 가장 많이 늘었다)
    industry_count: int


@dataclass(frozen=True)
class ConditionCompare:
    before: PeriodCondition
    recent: PeriodCondition

    @property
    def direction(self) -> Direction:
        delta = self.recent.excess_pct - self.before.excess_pct
        if delta <= -STEADY_BAND:
            return "weaker"
        if delta >= STEADY_BAND:
            return "stronger"
        return "similar"


def _growth(start: int, end: int) -> float:
    return (end - start) / start * 100


def period_condition(flows: list[IndustryFlows], target_id: str, window: Window) -> PeriodCondition | None:
    stocks = {f.industry_id: (f.stock_at(window.start), f.stock_at(window.end)) for f in flows}
    stocks = {industry: pair for industry, pair in stocks.items() if pair[0] > 0}
    target = next((f for f in flows if f.industry_id == target_id), None)
    if target is None or target_id not in stocks:
        return None
    start, end = stocks[target_id]
    growth = _growth(start, end)
    all_growth = _growth(sum(s for s, _ in stocks.values()), sum(e for _, e in stocks.values()))
    ranked = sorted(stocks, key=lambda industry: _growth(*stocks[industry]), reverse=True)
    closings = sum(count for m, count in target.closings.items() if window.start <= m < window.end)
    return PeriodCondition(
        window=window,
        growth_pct=round(growth, 1),
        all_growth_pct=round(all_growth, 1),
        excess_pct=round(growth - all_growth, 1),
        closure_rate_pct=round(closings / start * 100, 1),
        rank=ranked.index(target_id) + 1,
        industry_count=len(ranked),
    )


def condition_compare(
    flows: list[IndustryFlows], target_id: str, event_start: date, today: date
) -> ConditionCompare | None:
    """이벤트 달 직전 12개월 vs 마지막 완결 12개월. 두 창이 겹치면(최근 이벤트) 견주지 않는다."""
    before = Window(add_months(month_of(event_start), -CONDITION_MONTHS), CONDITION_MONTHS)
    recent = Window(add_months(month_of(today), -CONDITION_MONTHS), CONDITION_MONTHS)
    if before.end > recent.start:
        return None
    before_condition = period_condition(flows, target_id, before)
    recent_condition = period_condition(flows, target_id, recent)
    if before_condition is None or recent_condition is None:
        return None
    return ConditionCompare(before_condition, recent_condition)
