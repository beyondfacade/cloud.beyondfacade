"""업종 하나의 월별 개폐업 흐름과 기간 창의 변동폭.

점포수는 흐름을 누적해 얻는다 — 어떤 달 1일의 점포수 = 그 전까지의 개업 합 − 폐업 합.
변동폭은 계절성을 지우려고 **전년 같은 달**과 비교한다(12월 폐업 몰림도 같은 달끼리라 상쇄된다).
"""

from dataclasses import dataclass
from datetime import date

from apps.shock.domain.services.event_window import Window


def _pct(value: float, base: float) -> float | None:
    if base <= 0:
        return None
    return round((value - base) / base * 100, 1)


@dataclass(frozen=True)
class WindowChange:
    openings: int
    closings: int
    openings_yoy_pct: float | None  # 전년 같은 달 대비 개업 증감률
    closings_yoy_pct: float | None  # 전년 같은 달 대비 폐업 증감률
    stock_change_pct: float | None  # 창 동안 점포수 증감률
    excess_pct: float | None  # 점포수 증감률 − 전년 같은 창의 증감률 (%p) — 평소보다 얼마나 더 늘었나


@dataclass(frozen=True)
class IndustryFlows:
    industry_id: str
    industry_name: str
    openings: dict[date, int]  # 달의 1일 → 개업 수
    closings: dict[date, int]  # 달의 1일 → 폐업 수

    def stock_at(self, month: date) -> int:
        """그 달 1일의 영업 점포수."""
        opened = sum(count for m, count in self.openings.items() if m < month)
        closed = sum(count for m, count in self.closings.items() if m < month)
        return opened - closed

    def _total(self, counts: dict[date, int], window: Window) -> int:
        return sum(count for m, count in counts.items() if window.start <= m < window.end)

    def _stock_growth(self, window: Window) -> float | None:
        before = self.stock_at(window.start)
        if before <= 0:
            return None
        return (self.stock_at(window.end) - before) / before * 100

    def change(self, window: Window) -> WindowChange:
        last_year = window.shifted(-12)
        openings = self._total(self.openings, window)
        closings = self._total(self.closings, window)
        growth = self._stock_growth(window)
        base_growth = self._stock_growth(last_year)
        return WindowChange(
            openings=openings,
            closings=closings,
            openings_yoy_pct=_pct(openings, self._total(self.openings, last_year)),
            closings_yoy_pct=_pct(closings, self._total(self.closings, last_year)),
            stock_change_pct=None if growth is None else round(growth, 1),
            excess_pct=None
            if growth is None or base_growth is None
            else round(growth - base_growth, 1),
        )
