"""업종 하나의 월별 개폐업 흐름과 기간 창의 변동폭.

점포수는 흐름을 누적해 얻는다 — 어떤 달 1일의 점포수 = 그 전까지의 개업 합 − 폐업 합.
변동폭은 계절성을 지우려고 **같은 달로 된 기준 창**과 비교한다(12월 폐업 몰림도 같은 달끼리라 상쇄된다).
"""

from bisect import bisect_left
from dataclasses import dataclass
from datetime import date
from functools import cached_property
from itertools import accumulate

from apps.shock.domain.services.event_window import Window


def _pct(value: float, base: float) -> float | None:
    if base <= 0:
        return None
    return round((value - base) / base * 100, 1)


@dataclass(frozen=True)
class WindowChange:
    openings: int
    closings: int
    openings_yoy_pct: float | None  # 기준 창 대비 개업 증감률
    closings_yoy_pct: float | None  # 기준 창 대비 폐업 증감률
    stock_change_pct: float | None  # 창 동안 점포수 증감률
    excess_pct: float | None  # 점포수 증감률 − 기준 창의 증감률 (%p) — 평소보다 얼마나 더 늘었나


def _cumulative(counts: dict[date, int]) -> tuple[list[date], list[int]]:
    months = sorted(counts)
    return months, list(accumulate(counts[m] for m in months))


def _sum_before(table: tuple[list[date], list[int]], month: date) -> int:
    months, totals = table
    position = bisect_left(months, month)
    return totals[position - 1] if position else 0


@dataclass(frozen=True)
class IndustryFlows:
    """흐름은 만든 뒤 바꾸지 않는다 — 누적합을 처음 조회할 때 한 번 만든다."""

    industry_id: str
    industry_name: str
    openings: dict[date, int]  # 달의 1일 → 개업 수
    closings: dict[date, int]  # 달의 1일 → 폐업 수

    @cached_property
    def _opened(self) -> tuple[list[date], list[int]]:
        return _cumulative(self.openings)

    @cached_property
    def _closed(self) -> tuple[list[date], list[int]]:
        return _cumulative(self.closings)

    def stock_at(self, month: date) -> int:
        """그 달 1일의 영업 점포수."""
        return _sum_before(self._opened, month) - _sum_before(self._closed, month)

    def _total(self, counts: dict[date, int], window: Window) -> int:
        return sum(count for m, count in counts.items() if window.start <= m < window.end)

    def _stock_growth(self, window: Window) -> float | None:
        before = self.stock_at(window.start)
        if before <= 0:
            return None
        return (self.stock_at(window.end) - before) / before * 100

    def change(self, window: Window, baseline: Window) -> WindowChange:
        openings = self._total(self.openings, window)
        closings = self._total(self.closings, window)
        growth = self._stock_growth(window)
        base_growth = self._stock_growth(baseline)
        return WindowChange(
            openings=openings,
            closings=closings,
            openings_yoy_pct=_pct(openings, self._total(self.openings, baseline)),
            closings_yoy_pct=_pct(closings, self._total(self.closings, baseline)),
            stock_change_pct=None if growth is None else round(growth, 1),
            excess_pct=None
            if growth is None or base_growth is None
            else round(growth - base_growth, 1),
        )
