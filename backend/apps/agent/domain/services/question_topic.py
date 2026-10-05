"""질문 → 유형 (stdlib만). 설계서 docs/superpowers/specs/2026-10-05-question-answer-design.md §4.

규칙 표를 위에서부터 훑어 처음 걸린 하나를 쓴다(Chain of Responsibility) — 여러 유형이 섞인 질문은 순위로 정한다.
LLM을 부르지 않는다 — 같은 질문은 늘 같은 유형이다.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class QuestionTopic:
    kind: str  # loan·budget·hours·competition·customers·covid·general
    detail: str | None = None  # hours: lunch·evening·night·morning·weekend / customers: foreign


# 시간대 낱말 → 구간. 문장에서 먼저 나온 낱말의 구간을 쓴다.
_BANDS = (
    ("점심", "lunch"),
    ("저녁", "evening"),
    ("밤", "night"),
    ("늦게", "night"),
    ("새벽", "night"),
    ("아침", "morning"),
    ("주말", "weekend"),
    ("평일", "weekend"),
)
_FOREIGN = re.compile(r"외국인|중국인")


def _no_detail(text: str) -> None:
    return None


def _band(text: str) -> str:
    return min((text.find(word), band) for word, band in _BANDS if word in text)[1]


def _foreign(text: str) -> str | None:
    return "foreign" if _FOREIGN.search(text) else None


# (유형, 걸리는 낱말, 세부) — 순위 순서다
_RULES: tuple[tuple[str, re.Pattern, Callable[[str], str | None]], ...] = (
    ("loan", re.compile(r"대출|빌려|융자"), _no_detail),
    ("budget", re.compile(r"\d+(?:\.\d+)?\s*(?:억|천만|천|만)\s*원|모아 ?둔 돈|자본금|예산"), _no_detail),
    ("hours", re.compile("|".join(word for word, _ in _BANDS)), _band),
    ("competition", re.compile(r"이미 많|벌써 여러|경쟁|포화"), _no_detail),
    ("customers", re.compile(r"외국인|중국인|어르신|노인|학생|직장인|주민|손님층"), _foreign),
    ("covid", re.compile(r"코로나|팬데믹"), _no_detail),
)


def classify(question: str | None) -> QuestionTopic | None:
    """질문 → 유형. 질문이 없거나 공백이면 None(총평), 어느 규칙에도 안 걸리면 general."""
    text = (question or "").strip()
    if not text:
        return None
    for kind, pattern, detail in _RULES:
        if pattern.search(text):
            return QuestionTopic(kind, detail(text))
    return QuestionTopic("general")
