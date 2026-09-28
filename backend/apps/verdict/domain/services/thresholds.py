"""판정 임계값 — 상수는 백분위 두 개와 표본 가드뿐이고, 실제 경계값(예: 한식 순유출 75백분위 = 0.083)은
배치마다 그 분포에서 다시 나온다. 어디에도 절대값을 하드코딩하지 않는다 (설계서 §3-2, typology.py 원칙)."""

from collections.abc import Sequence
from dataclasses import dataclass

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    LEVEL_OFF,
    LEVEL_ON,
    LEVEL_STRONG,
)


@dataclass(frozen=True)
class VerdictThresholds:
    on_percentile: float = 75.0
    strong_percentile: float = 90.0
    min_sample: int = 10  # 순유출 시작 점포·코호트·폐업 건수 가드
    min_population: int = 1000  # 포화 분모(상주인구) 가드
    min_evaluable: int = 3  # 판정 가능한 신호가 이보다 적으면 보류


DEFAULT_THRESHOLDS = VerdictThresholds()


def percentile_rank(value: float, distribution: Sequence[float]) -> float:
    """value보다 작은 값의 비율 × 100 (strict). 동률이 많아도 전부 켜지지 않는다."""
    if not distribution:
        return 0.0
    below = sum(1 for other in distribution if other < value)
    return below / len(distribution) * 100.0


def level_of(percentile: float, thresholds: VerdictThresholds) -> str:
    """백분위 → 레벨. 순서 비교라 조건문이 맞다 (타입·상태 분기가 아니다)."""
    if percentile >= thresholds.strong_percentile:
        return LEVEL_STRONG
    if percentile >= thresholds.on_percentile:
        return LEVEL_ON
    return LEVEL_OFF
