"""판정 임계값 — 백분위는 strict, 75/90 경계, 상수는 dataclass 한 곳."""

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    EXCLUDED_INDUSTRIES,
    LEVEL_OFF,
    LEVEL_ON,
    LEVEL_STRONG,
    SIGNAL_KEYS,
)
from apps.verdict.domain.services.thresholds import (
    DEFAULT_THRESHOLDS,
    VerdictThresholds,
    level_of,
    percentile_rank,
)


def test_백분위는_값보다_작은_동의_비율이다_strict():
    distribution = [1.0, 2.0, 3.0, 4.0]
    assert percentile_rank(3.0, distribution) == 50.0  # 1,2 두 개가 작다
    assert percentile_rank(0.5, distribution) == 0.0
    assert percentile_rank(9.0, distribution) == 100.0


def test_동률이_많은_이진값은_전부_켜지지_않는다():
    distribution = [1.0] * 10
    assert percentile_rank(1.0, distribution) == 0.0


def test_빈_분포는_0이다():
    assert percentile_rank(5.0, []) == 0.0


def test_레벨_경계_75_90():
    t = DEFAULT_THRESHOLDS
    assert level_of(74.9, t) == LEVEL_OFF
    assert level_of(75.0, t) == LEVEL_ON
    assert level_of(89.9, t) == LEVEL_ON
    assert level_of(90.0, t) == LEVEL_STRONG


def test_기본_임계값_상수():
    assert DEFAULT_THRESHOLDS == VerdictThresholds(
        on_percentile=75.0, strong_percentile=90.0, min_sample=10, min_population=1000, min_evaluable=3
    )


def test_신호_키_순서와_제외_업종():
    assert SIGNAL_KEYS == ("net_outflow", "survival_cliff", "early_closure", "saturation", "shrinking")
    assert EXCLUDED_INDUSTRIES == frozenset(
        {"academy", "childcare", "restaurant_other", "chicken", "convenience_store", "real_estate"}
    )
