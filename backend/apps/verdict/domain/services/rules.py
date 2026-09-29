"""판정 규칙 — 결정 목록 (Chain of Responsibility, CLAUDE.md §5). 첫 일치가 이긴다.
보류를 먼저 검사한다: 표본 부족 동을 ⚪로 오해하지 않기 위해 (설계서 §3-3)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from apps.verdict.domain.entities.region_industry_verdict_entity import (
    ADVISORY_SIGNAL_KEYS,
    LEVEL_ON,
    LEVEL_STRONG,
    LEVEL_UNAVAILABLE,
    VERDICT_CLEAR,
    VERDICT_INSUFFICIENT,
    VERDICT_ORANGE,
    VERDICT_RED,
    SignalResult,
)
from apps.verdict.domain.services.thresholds import VerdictThresholds


def strong_count(results: Sequence[SignalResult]) -> int:
    return sum(1 for r in results if r.key not in ADVISORY_SIGNAL_KEYS and r.level == LEVEL_STRONG)


def on_count(results: Sequence[SignalResult]) -> int:
    return sum(1 for r in results if r.key not in ADVISORY_SIGNAL_KEYS and r.level in (LEVEL_ON, LEVEL_STRONG))


def evaluable_count(results: Sequence[SignalResult]) -> int:
    return sum(1 for r in results if r.key not in ADVISORY_SIGNAL_KEYS and r.level != LEVEL_UNAVAILABLE)


class VerdictRule(ABC):
    @abstractmethod
    def judge(self, results: Sequence[SignalResult], t: VerdictThresholds) -> str | None:
        """판정되면 코드, 아니면 None을 반환해 다음 규칙에 넘긴다."""


class InsufficientRule(VerdictRule):
    def judge(self, results, t):
        return VERDICT_INSUFFICIENT if evaluable_count(results) < t.min_evaluable else None


class RedRule(VerdictRule):
    def judge(self, results, t):
        return VERDICT_RED if strong_count(results) >= 2 else None


class OrangeRule(VerdictRule):
    def judge(self, results, t):
        return VERDICT_ORANGE if on_count(results) >= 1 else None


class ClearRule(VerdictRule):
    def judge(self, results, t):
        return VERDICT_CLEAR


RULES: tuple[VerdictRule, ...] = (InsufficientRule(), RedRule(), OrangeRule(), ClearRule())


def judge(results: Sequence[SignalResult], t: VerdictThresholds) -> str:
    for rule in RULES:
        verdict = rule.judge(results, t)
        if verdict is not None:
            return verdict
    raise AssertionError("ClearRule은 항상 판정한다")
