"""risk_band — 위험 백분위 → 5단계 등급 (판정 임계값과 같은 경계)."""

import pytest

from apps.verdict.domain.services.risk_band import band_of
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS


@pytest.mark.parametrize(
    ("percentile", "band"),
    [(95.0, "very_bad"), (90.0, "very_bad"), (89.9, "bad"), (75.0, "bad"), (74.9, "normal"),
     (25.0, "normal"), (24.9, "good"), (10.0, "good"), (9.9, "very_good"), (0.0, "very_good")],
)
def test_위험_백분위를_판정_임계값과_같은_경계의_다섯_등급으로_나눈다(percentile, band):
    assert band_of(percentile, DEFAULT_THRESHOLDS) == band
