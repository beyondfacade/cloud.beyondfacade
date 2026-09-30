"""이벤트 기점의 분기 — 이벤트가 시작된 달부터 3개월씩, 끝나지 않은 달이 든 분기는 쓰지 않는다.

- 분기는 달력 분기가 아니라 이벤트 기준이다(5월에 시작했으면 1분기는 5~7월).
  1분기가 '직후 3개월', 4분기가 '1년 차 마지막 3개월'이다.
- 분기마다 **이벤트 직전 1년의 같은 분기**와 견준다. 같은 달끼리라 계절성이 지워지고,
  2·3년 차도 이벤트에 물든 1년 차가 아니라 이벤트 전과 비교한다.
"""

from dataclasses import dataclass
from datetime import date

QUARTER_MONTHS = 3
QUARTERS_PER_YEAR = 4
YEARS_RANGE = range(1, 4)


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
    start: date  # 창 첫 달의 1일
    months: int

    @property
    def end(self) -> date:
        """창 다음 달의 1일 (배타)."""
        return add_months(self.start, self.months)

    def shifted(self, count: int) -> "Window":
        return Window(add_months(self.start, count), self.months)


@dataclass(frozen=True)
class Quarter:
    index: int  # 이벤트 기준 0부터
    window: Window

    @property
    def year(self) -> int:
        return self.index // QUARTERS_PER_YEAR + 1

    @property
    def number(self) -> int:
        return self.index % QUARTERS_PER_YEAR + 1

    @property
    def baseline(self) -> Window:
        """이벤트 직전 1년의 같은 분기."""
        return self.window.shifted(-12 * self.year)


def check_years(years: int) -> None:
    if years not in YEARS_RANGE:
        raise ValueError(f"비교 연수는 {YEARS_RANGE.start}~{YEARS_RANGE.stop - 1}년 사이여야 합니다")


def event_quarters(start_date: date, today: date, years: int) -> list[Quarter]:
    check_years(years)
    first = month_of(start_date)
    complete_until = month_of(today)  # 이번 달은 아직 집계가 끝나지 않았다
    quarters: list[Quarter] = []
    for index in range(QUARTERS_PER_YEAR * years):
        window = Window(add_months(first, QUARTER_MONTHS * index), QUARTER_MONTHS)
        if window.end > complete_until:
            break
        quarters.append(Quarter(index, window))
    return quarters
