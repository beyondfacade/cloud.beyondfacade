"""신호 프로필 — 원천별 신호 목록·원천 표기·미지원 신호·폐업률·담배권 빈자리 (업종 특화 신호 설계서 §4·§6·§7)."""

import pytest

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    ADVISORY_SIGNAL_KEYS,
    ALL_SIGNAL_KEYS,
    LEVEL_OFF,
    LEVEL_STRONG,
    LEVEL_UNAVAILABLE,
    SIGNAL_KEYS,
    SignalResult,
)
from apps.verdict.domain.services.profiles import AggregateProfile, PermitProfile, TobaccoProxyProfile
from apps.verdict.domain.services.rules import on_count, strong_count
from apps.verdict.domain.services.signals import ClosureRateSignal, SignalInput, TobaccoGapSignal
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS as T


def _input(**overrides) -> SignalInput:
    base = dict(
        region_code="1168064000", industry_id="convenience_store", industry_name="편의점",
        start_store_count=100, opened_12m=28, closed_12m=41,
        cohort_size=37, cohort_survived=14,
        closed_3y_count=60, closed_3y_median_months=19.0,
        latest_store_count=94, resident_total=10_000,
        change_code="HL", change_name="상권축소", change_quarter="20262",
        closed_months=20.0, seoul_closed_months=27.0,
        gap_candidates=200, gap_blocked=150,
    )
    base.update(overrides)
    return SignalInput(**base)


def test_신호_키_상수와_빈자리_가드():
    assert ALL_SIGNAL_KEYS == SIGNAL_KEYS + ("closure_rate", "tobacco_gap", "trade_per_office")
    assert T.min_gap_candidates == 30


def test_인허가_프로필은_공통_신호_5개_그대로다():
    profile = PermitProfile()
    assert profile.basis == "permit"
    assert tuple(s.key for s in profile.signals()) == SIGNAL_KEYS


def test_편의점_프로필은_공통_5개에_담배권_빈자리를_더하고_원천을_담배소매인으로_표기한다():
    profile = TobaccoProxyProfile()
    assert profile.basis == "proxy"
    assert tuple(s.key for s in profile.signals()) == SIGNAL_KEYS + ("tobacco_gap",)
    results = {s.key: s.evaluate(_input(), T, [0.0, 0.5]) for s in profile.signals()}
    assert results["net_outflow"].source == "tobacco"
    assert results["net_outflow"].value == pytest.approx(0.13)
    assert results["saturation"].source == "tobacco"
    assert results["shrinking"].source == "neighborhood"
    assert results["tobacco_gap"].source == "tobacco"


def test_부동산_프로필은_폐업률과_포화만_계산하고_코호트_신호는_집계_사유로_미판정이다():
    profile = AggregateProfile()
    assert profile.basis == "aggregate"
    assert tuple(s.key for s in profile.signals()) == (
        "closure_rate", "survival_cliff", "early_closure", "saturation", "shrinking", "trade_per_office",
    )
    results = {s.key: s.evaluate(_input(), T, [0.1]) for s in profile.signals()}
    for key in ("survival_cliff", "early_closure"):
        assert results[key].level == LEVEL_UNAVAILABLE
        assert results[key].evidence == "집계 원천 — 개별 점포 개업·폐업일이 없어 산출하지 않음"
        assert results[key].source == "commerce"
    assert results["closure_rate"].source == "commerce"
    assert results["saturation"].source == "commerce"
    unsupported = [s for s in profile.signals() if s.key in ("survival_cliff", "early_closure")]
    assert all(s.raw_value(_input(), T) is None for s in unsupported)  # 분포에도 안 들어간다


def test_폐업률은_4분기_폐업을_시작_점포로_나누고_가드는_10이다():
    signal = ClosureRateSignal()
    assert signal.raw_value(_input(), T) == pytest.approx(0.41)
    assert signal.raw_value(_input(start_store_count=9), T) is None
    result = signal.evaluate(_input(), T, [0.1, 0.2, 0.3, 0.4])
    assert result.level == LEVEL_STRONG
    assert "지난 4분기 폐업 41곳" in result.evidence and "서울시 상권분석 집계" in result.evidence
    assert "표본 부족" in signal.evaluate(_input(start_store_count=9), T, [0.1]).evidence


def test_담배권_빈자리는_막힌_자리_비율이고_후보_30곳_미만이면_미판정이다():
    signal = TobaccoGapSignal()
    assert signal.raw_value(_input(), T) == pytest.approx(0.75)
    thin = signal.evaluate(_input(gap_candidates=29, gap_blocked=29), T, [0.5])
    assert thin.level == LEVEL_UNAVAILABLE and "29곳" in thin.evidence
    ok = signal.evaluate(_input(), T, [0.5, 0.6])
    assert "50m" in ok.evidence and "200곳" in ok.evidence and "75%" in ok.evidence


def test_담배권_빈자리는_참고_신호라_등급_계산에서_빠진다():
    assert "tobacco_gap" in ADVISORY_SIGNAL_KEYS and "shrinking" in ADVISORY_SIGNAL_KEYS
    results = [
        SignalResult("tobacco_gap", LEVEL_STRONG, 0.9, 99.0, "근거", "tobacco"),
        SignalResult("net_outflow", LEVEL_OFF, 0.0, 10.0, "근거", "tobacco"),
    ]
    assert strong_count(results) == 0 and on_count(results) == 0
