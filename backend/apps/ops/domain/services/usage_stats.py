import math
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LlmUsageRecord:
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


@dataclass(frozen=True)
class ModelUsage:
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    avg_latency_ms: int


@dataclass(frozen=True)
class UsageSummary:
    window_hours: int
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    p50_latency_ms: int | None = None
    p95_latency_ms: int | None = None
    by_model: list[ModelUsage] = field(default_factory=list)


def percentile(values: list[int], p: int) -> int | None:
    """최근접 순위 백분위 — 표본이 적어도 실제 관측값을 돌려준다."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p / 100 * len(ordered)) - 1)]


def summarize_usage(records: list[LlmUsageRecord], window_hours: int) -> UsageSummary:
    grouped: dict[str, list[LlmUsageRecord]] = defaultdict(list)
    for record in records:
        grouped[record.model].append(record)
    by_model = [
        ModelUsage(
            model=model,
            calls=len(rows),
            input_tokens=sum(r.input_tokens for r in rows),
            output_tokens=sum(r.output_tokens for r in rows),
            avg_latency_ms=round(sum(r.latency_ms for r in rows) / len(rows)),
        )
        for model, rows in grouped.items()
    ]
    latencies = [r.latency_ms for r in records]
    return UsageSummary(
        window_hours=window_hours,
        calls=len(records),
        input_tokens=sum(r.input_tokens for r in records),
        output_tokens=sum(r.output_tokens for r in records),
        p50_latency_ms=percentile(latencies, 50),
        p95_latency_ms=percentile(latencies, 95),
        by_model=sorted(by_model, key=lambda m: -m.calls),
    )
