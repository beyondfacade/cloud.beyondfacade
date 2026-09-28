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
from apps.verdict.domain.services.rules import judge, on_count, strong_count
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


def test_판정_가능_신호_3개_미만이면_강한_신호가_2개여도_보류():
    levels = (LEVEL_STRONG, LEVEL_STRONG, LEVEL_UNAVAILABLE, LEVEL_UNAVAILABLE, LEVEL_UNAVAILABLE)
    assert judge(_results(*levels), T) == VERDICT_INSUFFICIENT


def test_카운트():
    r = _results(LEVEL_STRONG, LEVEL_ON, LEVEL_OFF, LEVEL_UNAVAILABLE, LEVEL_STRONG)
    assert strong_count(r) == 2
    assert on_count(r) == 3  # on + strong
