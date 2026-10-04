"""모델 평가 공통 통계 — 임베딩(rag)·LLM(agent·intent) 하네스가 함께 쓴다 (numpy만).

판정 원칙(2026-10-04 사용자 결정): 주 지표 1위와 paired bootstrap 95% 구간이 0을 포함하면 동률,
동률 중 비용(임베딩=차원, LLM=VRAM)이 작은 순 → p95가 짧은 순.
"""

from statistics import mean

import numpy as np


def paired_bootstrap_ci(
    a: list[float], b: list[float], n: int = 10_000, seed: int = 0
) -> tuple[float, float, float]:
    """문항별 점수 차이(a−b)의 평균과 95% 구간. 하한 ≤ 0 ≤ 상한이면 동률."""
    if len(a) != len(b):
        raise ValueError(f"문항 수가 다르다: {len(a)} != {len(b)}")
    x = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), size=(n, len(x)))].mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(x.mean()), float(lo), float(hi)


def percentile(samples: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(samples, dtype=np.float64), q))


def resident_models(ps_json: dict) -> set[str]:
    """Ollama /api/ps 응답 → 지금 메모리에 올라 있는 모델 이름."""
    return {m["name"] for m in ps_json.get("models", [])}


def pick_winner(
    score_by: dict[str, list[float]], cost_by: dict[str, float], p95_by: dict[str, float | None], eligible: list[str]
) -> tuple[str, list[str]]:
    """평균 점수 1위와 bootstrap 동률인 후보 중 (비용, p95, 이름) 최소. 반환: (승자, 동률 목록)."""
    best = max(eligible, key=lambda c: (mean(score_by[c]), -cost_by[c]))
    tied = sorted(c for c in eligible if c == best or paired_bootstrap_ci(score_by[best], score_by[c])[1] <= 0)
    winner = min(tied, key=lambda c: (cost_by[c], p95_by.get(c) or float("inf"), c))
    return winner, tied
