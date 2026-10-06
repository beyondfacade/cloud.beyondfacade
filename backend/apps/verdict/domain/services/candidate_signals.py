"""백테스트 전용 후보 신호 — 운영 판정(signals.SIGNALS)에 넣지 않는다. 여러 시점 백테스트(backtest_multi CLI)만 쓴다.
원값은 운영 신호와 같은 관례로 낸다: 가드 미달이면 None(분포·집계에서 빠짐), 업종 안 백분위가 on_percentile 이상이면 켜짐.
순수 파이썬."""

from collections.abc import Callable, Iterable, Mapping, Sequence

from apps.verdict.app.dtos.region_industry_verdict_dto import EntrantOutcome
from apps.verdict.domain.services.backtest import SignalBucket
from apps.verdict.domain.services.thresholds import percentile_rank

Key = tuple[str, str]  # (region_code, industry_id)


def saturation_demand(store_count: int | None, demand: int | None, min_demand: int) -> float | None:
    """수요 1,000명당 점포수 — 포화(상주인구 분모)의 분모만 수요로 바꾼 것. 높을수록 나쁨."""
    if store_count is None or demand is None or demand < min_demand:
        return None
    return store_count / (demand / 1000)


def opening_rush(opened_12m: int, start_store_count: int, min_sample: int) -> float | None:
    """T 전 12개월 개업 ÷ 12개월 전 영업 점포 — 높을수록 나쁨(공급 몰림)."""
    if start_store_count < min_sample:
        return None
    return opened_12m / start_store_count


def sales_trend(
    sales_now: int | None, stores_now: int | None, sales_prev: int | None, stores_prev: int | None, min_sample: int
) -> float | None:
    """점포당 분기 매출의 전년 동분기 대비 변화율 — 낮을수록(하락) 나쁨."""
    if None in (sales_now, stores_now, sales_prev, stores_prev) or min(stores_now, stores_prev) < min_sample:
        return None
    if not sales_prev:
        return None
    return (sales_now / stores_now) / (sales_prev / stores_prev) - 1


def fired_flags(
    values: Mapping[Key, float | None], worse: Callable[[float], float], on_percentile: float
) -> dict[Key, bool]:
    """업종 안에서 가드를 통과한 값끼리 백분위를 내 on_percentile 이상이면 켜짐. None은 결과에서 뺀다."""
    distributions: dict[str, list[float]] = {}
    for (_, industry), value in values.items():
        if value is not None:
            distributions.setdefault(industry, []).append(worse(value))
    return {
        key: percentile_rank(worse(value), distributions[key[1]]) >= on_percentile
        for key, value in values.items()
        if value is not None
    }


def summarize_candidate(key: str, fired: Mapping[Key, bool], outcomes: Iterable[EntrantOutcome]) -> list[SignalBucket]:
    """켜진 동×업종 vs 꺼진 동×업종의 진입 코호트 폐업 — 전체(None)와 업종별. 운영 summarize_signals와 같은 셈법."""
    by_key = {(o.region_code, o.industry_id): o for o in outcomes}
    acc: dict[tuple[str | None, bool], list[int]] = {}
    for (region, industry), on in fired.items():
        o = by_key.get((region, industry))
        opened, closed = (o.opened, o.closed_within) if o else (0, 0)
        for scope in (None, industry):
            cell = acc.setdefault((scope, on), [0, 0, 0])
            cell[0] += 1
            cell[1] += opened
            cell[2] += closed
    ordered = sorted(acc, key=lambda k: (k[0] is not None, k[0] or "", not k[1]))
    return [SignalBucket(scope, key, on, *acc[(scope, on)]) for scope, on in ordered]


def stable_hits(
    cells: Sequence[tuple[float, int, int] | None], min_lift: float, min_opened: int
) -> tuple[int, int]:
    """(lift, 켜짐 개업, 꺼짐 개업) 시점 목록 → (표본 충분 & lift ≥ min_lift인 시점 수, 표본 충분한 시점 수)."""
    sampled = [lift for lift, on, off in (c for c in cells if c is not None) if min(on, off) >= min_opened]
    return sum(1 for lift in sampled if lift >= min_lift), len(sampled)
