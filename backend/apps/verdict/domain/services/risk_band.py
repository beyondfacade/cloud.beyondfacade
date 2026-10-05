"""위험 백분위 → 5단계 등급 (stdlib·도메인만). 경고·강한 경고 경계는 판정 임계값(75·90)을 그대로 쓰고,
좋은 쪽 두 경계(25·10)는 그 대칭이다 — 근거 문장의 등급 낱말이 판정과 어긋나지 않게 한다."""

from apps.verdict.domain.services.thresholds import VerdictThresholds

BANDS = ("very_bad", "bad", "normal", "good", "very_good")
_GOOD_PERCENTILE = 25.0  # on_percentile(75)의 대칭
_VERY_GOOD_PERCENTILE = 10.0  # strong_percentile(90)의 대칭


def band_of(percentile: float, thresholds: VerdictThresholds) -> str:
    """위험 백분위 → 등급 코드. 순서 비교라 조건 표를 위에서부터 훑는다."""
    for floor, band in (
        (thresholds.strong_percentile, "very_bad"),
        (thresholds.on_percentile, "bad"),
        (_GOOD_PERCENTILE, "normal"),
        (_VERY_GOOD_PERCENTILE, "good"),
    ):
        if percentile >= floor:
            return band
    return "very_good"
