"""이벤트 기점의 비교 기간 창 — 월 단위, 끝나지 않은 이번 달은 쓰지 않는다.

- 직후 창: 이벤트가 시작된 달부터 n개월.
- 이벤트 뒤 y년이 지났으면: y년 차의 마지막 n개월(늦은 창) — 충격이 굳었는지 풀렸는지를 본다.
- 아직 y년이 안 됐으면: 끝난 달 기준 최근 n개월(최근 창) — 지금까지 어디로 흘렀는지를 본다.
  최근 창이 직후 창과 겹치면 두 번째 창은 없다(같은 달을 두 번 세지 않는다).
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

MONTHS_RANGE = range(1, 4)
YEARS_RANGE = range(1, 4)


class WindowKind(StrEnum):
    IMMEDIATE = "immediate"
    LATE = "late"
    RECENT = "recent"


def month_of(day: date) -> date:
    return day.replace(day=1)


def add_months(month: date, count: int) -> date:
    index = month.year * 12 + month.month - 1 + count
    return date(index // 12, index % 12 + 1, 1)


def months_between(start: date, end: date) -> int:
    """두 날짜가 속한 달 사이의 개월 수 (end의 달 − start의 달)."""
    return (end.year - start.year) * 12 + end.month - start.month


@dataclass(frozen=True)
class Window:
    kind: WindowKind
    start: date  # 창 첫 달의 1일
    months: int

    @property
    def end(self) -> date:
        """창 다음 달의 1일 (배타)."""
        return add_months(self.start, self.months)

    def shifted(self, count: int) -> "Window":
        return Window(self.kind, add_months(self.start, count), self.months)


def check_window_size(months: int, years: int) -> None:
    if months not in MONTHS_RANGE or years not in YEARS_RANGE:
        raise ValueError(
            f"n개월은 {MONTHS_RANGE.start}~{MONTHS_RANGE.stop - 1}, "
            f"n년은 {YEARS_RANGE.start}~{YEARS_RANGE.stop - 1} 사이여야 합니다"
        )


def event_windows(start_date: date, today: date, months: int, years: int) -> list[Window]:
    check_window_size(months, years)
    first = month_of(start_date)
    complete_until = month_of(today)  # 이번 달은 아직 집계가 끝나지 않았다
    available = months_between(first, complete_until)
    if available <= 0:
        return []
    immediate = Window(WindowKind.IMMEDIATE, first, min(months, available))
    horizon = add_months(first, 12 * years)
    if horizon <= complete_until:
        return [immediate, Window(WindowKind.LATE, add_months(horizon, -months), months)]
    recent = Window(WindowKind.RECENT, add_months(complete_until, -months), months)
    if recent.start < immediate.end:
        return [immediate]
    return [immediate, recent]
