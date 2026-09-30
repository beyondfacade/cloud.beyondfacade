"""LLM 사용 시계열 — 분석 건수·토큰(llm_usage)과 호출 결과(llm_call_event)를 시간 버킷으로 묶는다."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
BUCKET_HOURS: dict[int, int] = {24: 1, 168: 6}  # 창(시간) → 버킷(시간): 24점·28점


@dataclass(frozen=True)
class TimedUsage:
    at: datetime
    tokens: int


@dataclass(frozen=True)
class LlmCallRecord:
    occurred_at: datetime
    model: str
    outcome: str  # ok | fallback | error
    latency_ms: int


@dataclass(frozen=True)
class UsagePoint:
    start: datetime
    analyses: int = 0
    tokens: int = 0
    ok: int = 0
    fallback: int = 0
    error: int = 0


@dataclass(frozen=True)
class CallOutcomes:
    """LLM 호출 시도 단위 — fallback은 '그 시도는 실패했지만 다음 모델이 받았다'."""

    attempts: int = 0
    ok: int = 0
    fallback: int = 0
    error: int = 0
    fallback_rate: float | None = None
    error_rate: float | None = None


def _floor_hour(at: datetime) -> datetime:
    return at.replace(minute=0, second=0, microsecond=0)


def bucket_starts(now: datetime, hours: int) -> list[datetime]:
    """마지막 버킷이 지금을 담도록 정시에 맞춘 버킷 시작 시각들 (오래된 것부터)."""
    step = timedelta(hours=BUCKET_HOURS[hours])
    last = _floor_hour(now)
    count = hours // BUCKET_HOURS[hours]
    return [last - step * k for k in reversed(range(count))]


def build_series(
    usage: list[TimedUsage], calls: list[LlmCallRecord], now: datetime, hours: int
) -> list[UsagePoint]:
    starts = bucket_starts(now, hours)
    step = timedelta(hours=BUCKET_HOURS[hours])
    first = starts[0]

    def index(at: datetime) -> int | None:
        position = int((at - first) / step)
        return position if 0 <= position < len(starts) else None

    analyses, tokens = Counter(), Counter()
    for row in usage:
        if (i := index(row.at)) is not None:
            analyses[i] += 1
            tokens[i] += row.tokens
    outcomes: dict[str, Counter] = {"ok": Counter(), "fallback": Counter(), "error": Counter()}
    for call in calls:
        if (i := index(call.occurred_at)) is not None and call.outcome in outcomes:
            outcomes[call.outcome][i] += 1
    return [
        UsagePoint(
            start=start,
            analyses=analyses[i],
            tokens=tokens[i],
            ok=outcomes["ok"][i],
            fallback=outcomes["fallback"][i],
            error=outcomes["error"][i],
        )
        for i, start in enumerate(starts)
    ]


def summarize_calls(calls: list[LlmCallRecord]) -> CallOutcomes:
    counts = Counter(call.outcome for call in calls)
    attempts = len(calls)
    return CallOutcomes(
        attempts=attempts,
        ok=counts["ok"],
        fallback=counts["fallback"],
        error=counts["error"],
        fallback_rate=round(counts["fallback"] / attempts, 4) if attempts else None,
        error_rate=round(counts["error"] / attempts, 4) if attempts else None,
    )


def hour_of_day(times: list[datetime]) -> list[int]:
    """한국 시각 0~23시별 건수 — 언제 분석이 몰리는지."""
    counts = Counter(at.astimezone(KST).hour for at in times)
    return [counts[hour] for hour in range(24)]
