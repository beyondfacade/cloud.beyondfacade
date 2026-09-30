"""설비 지표 추세 규칙 — 표본 보존 기간과 차트 버킷 크기."""

import math
from datetime import timedelta

SAMPLE_RETENTION = timedelta(days=8)  # 7일 추세 + 하루 여유
MAX_POINTS = 240  # 차트 한 장의 점 수 상한 — 7일이면 42분 버킷


def bucket_seconds(hours: int) -> int:
    """hours 창을 MAX_POINTS 이하 점으로 — 분 단위로 올림, 최소 1분."""
    return max(60, math.ceil(hours * 3600 / MAX_POINTS / 60) * 60)


def percent(part: float | None, total: float | None) -> float | None:
    if part is None or not total:
        return None
    return round(part / total * 100, 1)
