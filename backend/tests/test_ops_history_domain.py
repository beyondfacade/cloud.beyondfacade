"""설비 추세·LLM 시계열·로그 가림 — 순수 도메인 규칙."""

from datetime import UTC, datetime, timedelta

from apps.ops.domain.services.host_history import bucket_seconds, percent
from apps.ops.domain.services.log_redaction import MASK, redact
from apps.ops.domain.services.usage_series import (
    LlmCallRecord,
    TimedUsage,
    bucket_starts,
    build_series,
    hour_of_day,
    summarize_calls,
)

NOW = datetime(2026, 9, 30, 12, 34, tzinfo=UTC)


def test_버킷은_240점_이하가_되도록_분_단위로_올린다():
    assert bucket_seconds(1) == 60
    assert bucket_seconds(24) == 360
    assert bucket_seconds(168) == 2520


def test_비율은_전체가_없거나_0이면_None():
    assert percent(1, 4) == 25.0
    assert percent(None, 4) is None
    assert percent(1, 0) is None


def test_24시간_창은_정시에_맞춘_1시간_버킷_24개다():
    starts = bucket_starts(NOW, 24)
    assert len(starts) == 24
    assert starts[-1] == datetime(2026, 9, 30, 12, tzinfo=UTC)
    assert starts[0] == datetime(2026, 9, 29, 13, tzinfo=UTC)


def test_7일_창은_6시간_버킷_28개다():
    assert len(bucket_starts(NOW, 168)) == 28


def test_시계열은_분석과_토큰과_호출_결과를_버킷에_나눠_담고_창_밖은_버린다():
    usage = [TimedUsage(NOW - timedelta(minutes=5), 100), TimedUsage(NOW - timedelta(hours=30), 999)]
    calls = [
        LlmCallRecord(NOW - timedelta(minutes=6), "gemini", "fallback", 900),
        LlmCallRecord(NOW - timedelta(minutes=5), "gemma", "ok", 3000),
        LlmCallRecord(NOW - timedelta(hours=2), "gemini", "error", 100),
    ]
    points = build_series(usage, calls, NOW, 24)
    assert (points[-1].analyses, points[-1].tokens, points[-1].ok, points[-1].fallback) == (1, 100, 1, 1)
    assert points[-3].error == 1
    assert sum(p.analyses for p in points) == 1


def test_호출_결과_요약은_시도_대비_폴백률과_오류율을_낸다():
    calls = [LlmCallRecord(NOW, "m", outcome, 1) for outcome in ("ok", "ok", "fallback", "error")]
    summary = summarize_calls(calls)
    assert (summary.attempts, summary.ok, summary.fallback, summary.error) == (4, 2, 1, 1)
    assert (summary.fallback_rate, summary.error_rate) == (0.25, 0.25)
    assert summarize_calls([]).fallback_rate is None


def test_시간대별_분포는_한국_시각_기준_24칸이다():
    counts = hour_of_day([datetime(2026, 9, 30, 0, 10, tzinfo=UTC), datetime(2026, 9, 30, 15, 0, tzinfo=UTC)])
    assert len(counts) == 24
    assert counts[9] == 1  # UTC 00시 = KST 09시
    assert counts[0] == 1  # UTC 15시 = KST 다음날 00시


def test_로그_가림은_쿼리_키와_베어러와_DB_비밀번호를_지운다():
    line = "GET https://apis.data.go.kr/x?serviceKey=AbC%2Bxyz&pageNo=1 Authorization: Bearer eyJhbGci.x.y"
    masked = redact(line)
    assert "AbC%2Bxyz" not in masked and "eyJhbGci" not in masked
    assert f"serviceKey={MASK}&pageNo=1" in masked
    assert redact("postgresql+psycopg://app:s3cr3t@db:5432/x") == f"postgresql+psycopg://app:{MASK}@db:5432/x"
    assert redact('{"api_key": "k-123", "n": 1}') == f'{{"api_key": "{MASK}", "n": 1}}'
    assert MASK in redact("key AIzaSyA1234567890abcdefghijk leaked")


def test_로그_가림은_평범한_줄을_건드리지_않는다():
    line = "[2026-09-30 05:10:00] funding collector 시작 — 312건 적재"
    assert redact(line) == line
