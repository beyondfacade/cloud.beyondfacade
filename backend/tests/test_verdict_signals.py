"""신호 5개 — 값·가드·나쁜 방향·근거 문장 (설계서 §3-1, §3-4)."""

import pytest

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    LEVEL_OFF,
    LEVEL_ON,
    LEVEL_STRONG,
    LEVEL_UNAVAILABLE,
    SIGNAL_KEYS,
)
from apps.verdict.domain.services.signals import (
    SIGNALS,
    EarlyClosureSignal,
    NetOutflowSignal,
    SaturationSignal,
    ShrinkingSignal,
    SignalInput,
    SurvivalCliffSignal,
)
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS as T


def _input(**overrides) -> SignalInput:
    base = dict(
        region_code="1168064000", industry_id="korean_food", industry_name="한식",
        start_store_count=100, opened_12m=28, closed_12m=41,
        cohort_size=37, cohort_survived=14,
        closed_3y_count=60, closed_3y_median_months=19.0,
        latest_store_count=94, resident_total=10_000,
        change_code="HL", change_name="상권축소", change_quarter="20262",
        closed_months=20.0, seoul_closed_months=27.0,
    )
    base.update(overrides)
    return SignalInput(**base)


def test_신호_순서와_키가_엔티티_상수와_같다():
    assert tuple(s.key for s in SIGNALS) == SIGNAL_KEYS


def test_순유출은_폐업에서_개업을_빼_시작_점포수로_나눈다():
    signal = NetOutflowSignal()
    assert signal.raw_value(_input(), T) == pytest.approx(0.13)
    assert signal.worse(0.13) == 0.13  # 높을수록 나쁨


def test_순유출_시작_점포_10_미만이면_미판정():
    result = NetOutflowSignal().evaluate(_input(start_store_count=9), T, [0.1, 0.2])
    assert result.level == LEVEL_UNAVAILABLE
    assert result.value is None and result.percentile is None
    assert "표본 부족" in result.evidence and "9곳" in result.evidence


def test_생존율은_낮을수록_나쁘다_부호_반전():
    signal = SurvivalCliffSignal()
    assert signal.raw_value(_input(), T) == pytest.approx(14 / 37)
    assert signal.worse(0.38) == -0.38


def test_생존_코호트_10_미만이면_미판정():
    assert SurvivalCliffSignal().raw_value(_input(cohort_size=9), T) is None


def test_조기폐업은_중위_개월이_낮을수록_나쁘다():
    signal = EarlyClosureSignal()
    assert signal.raw_value(_input(), T) == 19.0
    assert signal.worse(19.0) == -19.0
    assert signal.raw_value(_input(closed_3y_count=9), T) is None
    assert signal.raw_value(_input(closed_3y_median_months=None), T) is None


def test_포화는_상주인구_천명당_점포수():
    signal = SaturationSignal()
    assert signal.raw_value(_input(), T) == pytest.approx(9.4)
    assert signal.raw_value(_input(resident_total=999), T) is None
    assert signal.raw_value(_input(resident_total=None), T) is None
    assert signal.raw_value(_input(latest_store_count=None), T) is None


def test_백분위로_레벨이_정해지고_근거_문장에_숫자와_비교_기준이_들어간다():
    distribution = [float(i) / 100 for i in range(20)]  # 0.00 ~ 0.19
    result = NetOutflowSignal().evaluate(_input(), T, distribution)  # 0.13 → 13개가 작다 → 65
    assert result.level == LEVEL_OFF
    assert result.percentile == 65.0
    assert "폐업 41곳" in result.evidence and "개업 28곳" in result.evidence
    assert "서울 한식 상위 35%" in result.evidence
    strong = NetOutflowSignal().evaluate(_input(closed_12m=60), T, distribution)  # 0.32 → 100
    assert strong.level == LEVEL_STRONG


def test_상권축소는_이진이고_서울보다_빨리_닫히면_strong():
    signal = ShrinkingSignal()
    assert signal.evaluate(_input(), T, []).level == LEVEL_STRONG  # HL + 20 < 27
    assert signal.evaluate(_input(closed_months=30.0), T, []).level == LEVEL_ON
    assert signal.evaluate(_input(change_code="HH", change_name="정체"), T, []).level == LEVEL_OFF
    missing = signal.evaluate(_input(change_code=None, change_name=None, change_quarter=None), T, [])
    assert missing.level == LEVEL_UNAVAILABLE
    on = signal.evaluate(_input(closed_months=None), T, [])
    assert on.level == LEVEL_ON and on.percentile is None
    assert "2026년 2분기" in on.evidence and "동 전체 기준" in on.evidence
