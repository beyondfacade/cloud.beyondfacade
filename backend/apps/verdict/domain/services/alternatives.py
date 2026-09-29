"""대안 순위 규칙 — 두 축(동네 고정·업종 고정)이 같은 규칙을 쓴다 (설계서 §12).

후보는 clear·orange만: red는 비추천이라 대안이 아니고 insufficient는 근거가 없다.
정렬 키 (판정 순위, strong, on, id) — 기준(현재 동×업종)보다 키가 작은 것만 남긴다.
그래서 기준이 clear면 대안이 없고, insufficient면 clear·orange 전부가 대안이다.
"""

from collections.abc import Callable, Sequence

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    VERDICT_CLEAR,
    VERDICT_INSUFFICIENT,
    VERDICT_ORANGE,
    VERDICT_RED,
    RegionIndustryVerdict,
)

VERDICT_RANK: dict[str, int] = {VERDICT_CLEAR: 0, VERDICT_ORANGE: 1, VERDICT_RED: 2, VERDICT_INSUFFICIENT: 3}
CANDIDATE_CODES: frozenset[str] = frozenset({VERDICT_CLEAR, VERDICT_ORANGE})
ALTERNATIVE_LIMIT = 3


def signal_key(verdict: RegionIndustryVerdict) -> tuple[int, int, int]:
    return (VERDICT_RANK[verdict.verdict_code], verdict.strong_count, verdict.on_count)


def rank_alternatives(
    base: RegionIndustryVerdict,
    candidates: Sequence[RegionIndustryVerdict],
    key: Callable[[RegionIndustryVerdict], str],
    limit: int = ALTERNATIVE_LIMIT,
) -> list[RegionIndustryVerdict]:
    """`key`는 축의 식별자(동네 고정이면 industry_id, 업종 고정이면 region_code) — 동률의 안정 정렬 기준."""
    base_key = signal_key(base)
    better = [v for v in candidates if v.verdict_code in CANDIDATE_CODES and signal_key(v) < base_key]
    return sorted(better, key=lambda v: (signal_key(v), key(v)))[:limit]
