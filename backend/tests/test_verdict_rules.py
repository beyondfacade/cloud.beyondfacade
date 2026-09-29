"""판정 규칙 — 보류 우선, red/orange/clear (설계서 §3-3)."""

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    LEVEL_OFF,
    LEVEL_ON,
    LEVEL_STRONG,
    LEVEL_UNAVAILABLE,
    VERDICT_CLEAR,
    VERDICT_INSUFFICIENT,
    VERDICT_ORANGE,
    VERDICT_RED,
    SignalResult,
)
from apps.verdict.domain.services.rules import evaluable_count, judge, on_count, strong_count
from apps.verdict.domain.services.thresholds import DEFAULT_THRESHOLDS as T


def _results(*levels: str) -> tuple[SignalResult, ...]:
    return tuple(
        SignalResult(key=f"s{i}", level=lv, value=None, percentile=None, evidence="", source="store")
        for i, lv in enumerate(levels)
    )


def test_강한_신호_2개면_red():
    assert judge(_results(LEVEL_STRONG, LEVEL_STRONG, LEVEL_OFF, LEVEL_OFF, LEVEL_OFF), T) == VERDICT_RED


def test_켜진_신호_1개면_orange_강한_1개도_orange():
    assert judge(_results(LEVEL_ON, LEVEL_OFF, LEVEL_OFF, LEVEL_OFF, LEVEL_OFF), T) == VERDICT_ORANGE
    assert judge(_results(LEVEL_STRONG, LEVEL_ON, LEVEL_OFF, LEVEL_OFF, LEVEL_OFF), T) == VERDICT_ORANGE


def test_켜진_신호_없으면_clear():
    assert judge(_results(LEVEL_OFF, LEVEL_OFF, LEVEL_OFF, LEVEL_OFF, LEVEL_UNAVAILABLE), T) == VERDICT_CLEAR


def test_판정_가능_신호_2개_미만이면_강한_신호가_있어도_보류():
    levels = (LEVEL_STRONG, LEVEL_UNAVAILABLE, LEVEL_UNAVAILABLE, LEVEL_UNAVAILABLE, LEVEL_UNAVAILABLE)
    assert judge(_results(*levels), T) == VERDICT_INSUFFICIENT


def test_판정_가능_신호가_2개면_판정한다():
    # shrinking을 참고 신호로 뺀 뒤 판정 신호는 4개 — 그중 2개면 판정한다 (설계서 §7)
    levels = (LEVEL_STRONG, LEVEL_STRONG, LEVEL_UNAVAILABLE, LEVEL_UNAVAILABLE, LEVEL_UNAVAILABLE)
    assert judge(_results(*levels), T) == VERDICT_RED


def test_카운트():
    r = _results(LEVEL_STRONG, LEVEL_ON, LEVEL_OFF, LEVEL_UNAVAILABLE, LEVEL_STRONG)
    assert strong_count(r) == 2
    assert on_count(r) == 3  # on + strong


def _results_with_keys(**by_key: str) -> tuple[SignalResult, ...]:
    return tuple(
        SignalResult(key=key, level=lv, value=None, percentile=None, evidence="", source="store")
        for key, lv in by_key.items()
    )


def test_참고_신호_shrinking은_strong이어도_strong_count에서_빠진다():
    r = _results_with_keys(net_outflow=LEVEL_OFF, survival_cliff=LEVEL_OFF, early_closure=LEVEL_OFF,
                            saturation=LEVEL_OFF, shrinking=LEVEL_STRONG)
    assert strong_count(r) == 0


def test_참고_신호_shrinking은_on이어도_on_count에서_빠진다():
    r = _results_with_keys(net_outflow=LEVEL_OFF, survival_cliff=LEVEL_OFF, early_closure=LEVEL_OFF,
                            saturation=LEVEL_OFF, shrinking=LEVEL_ON)
    assert on_count(r) == 0


def test_참고_신호_shrinking은_evaluable_count에서_빠진다():
    r = _results_with_keys(net_outflow=LEVEL_UNAVAILABLE, survival_cliff=LEVEL_UNAVAILABLE,
                            early_closure=LEVEL_UNAVAILABLE, saturation=LEVEL_OFF, shrinking=LEVEL_STRONG)
    assert evaluable_count(r) == 1  # saturation만 — shrinking은 참고라 아예 세지 않는다


def test_참고_신호_shrinking_strong은_혼자서는_판정을_뒤집지_않는다():
    # 판정 신호 4개 전부 판정 가능(min_evaluable=2 충족) + off, shrinking만 strong → clear (red/orange 아님)
    r = _results_with_keys(net_outflow=LEVEL_OFF, survival_cliff=LEVEL_OFF, early_closure=LEVEL_OFF,
                            saturation=LEVEL_OFF, shrinking=LEVEL_STRONG)
    assert judge(r, T) == VERDICT_CLEAR
