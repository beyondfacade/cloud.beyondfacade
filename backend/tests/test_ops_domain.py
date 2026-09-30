"""ops BC 도메인 — 수집기 지연 판정·LLM 사용량 집계."""

from datetime import UTC, datetime, timedelta

from apps.ops.domain.services.collector_catalog import COLLECTORS, collector_status
from apps.ops.domain.services.usage_stats import LlmUsageRecord, percentile, summarize_usage

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def test_로그가_없으면_missing():
    assert collector_status(None, timedelta(days=1), NOW) == "missing"


def test_주기의_1_5배_안이면_ok_넘으면_late():
    assert collector_status(NOW - timedelta(hours=35), timedelta(days=1), NOW) == "ok"
    assert collector_status(NOW - timedelta(hours=37), timedelta(days=1), NOW) == "late"
    assert collector_status(NOW - timedelta(minutes=80), timedelta(hours=1), NOW) == "ok"
    assert collector_status(NOW - timedelta(minutes=100), timedelta(hours=1), NOW) == "late"


def test_수집기_카탈로그는_키가_겹치지_않고_크론_스크립트와_짝이다():
    keys = [c.key for c in COLLECTORS]
    assert len(keys) == len(set(keys))
    assert {"news-poller", "store-collector", "funding-collector", "rag-indexer"} <= set(keys)
    assert all(c.log_file.endswith(".log") for c in COLLECTORS)


def test_백분위는_최근접_순위로_구한다():
    assert percentile([], 50) is None
    assert percentile([100], 95) == 100
    assert percentile([10, 20, 30, 40, 50, 60, 70, 80, 90, 100], 50) == 50
    assert percentile([10, 20, 30, 40, 50, 60, 70, 80, 90, 100], 95) == 100


def test_사용량은_모델별로_묶고_전체_지연_분위를_낸다():
    records = [
        LlmUsageRecord(model="gemini-2.5-flash", input_tokens=1000, output_tokens=200, latency_ms=1000),
        LlmUsageRecord(model="gemini-2.5-flash", input_tokens=3000, output_tokens=400, latency_ms=3000),
        LlmUsageRecord(model="gemma4:12b", input_tokens=500, output_tokens=100, latency_ms=9000),
    ]
    summary = summarize_usage(records, window_hours=24)
    assert (summary.calls, summary.input_tokens, summary.output_tokens) == (3, 4500, 700)
    assert (summary.p50_latency_ms, summary.p95_latency_ms) == (3000, 9000)
    gemini = summary.by_model[0]
    assert (gemini.model, gemini.calls, gemini.avg_latency_ms) == ("gemini-2.5-flash", 2, 2000)
    assert [m.model for m in summary.by_model] == ["gemini-2.5-flash", "gemma4:12b"]
