"""리포트 벤치 채점 — 순수 로직(DB·네트워크 없음, 결정적).

숫자 지어내기 대조, 판정 일치, LLM 작성 절 판별, 블라인드 판정자 묶음.
"""

from __future__ import annotations

import json
import random
import re

_NUMBER_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(%|퍼센트|억|천만|백만|만|천)?")
_UNIT_MULT = {"억": 1e8, "천만": 1e7, "백만": 1e6, "만": 1e4, "천": 1e3}
_PERCENT_UNITS = {"%", "퍼센트"}
_SMALL_INT_MAX = 10
_YEAR_RANGE = range(1990, 2101)

VERDICT_LABELS = {"red": "비추천", "orange": "조건부", "clear": "경고 없음", "insufficient": "판정 보류"}
_ASSERTIVE_LABELS = ("비추천", "조건부", "경고 없음")  # 자료가 없을 때 쓰면 안 되는 단정 라벨

_FACTS_JSON_LIMIT = 3000


# ── 숫자 추출 ──────────────────────────────────────────────

def _split_token(m: re.Match) -> tuple[str, str, str | None]:
    """정규식 매치 → (원문 토큰, 숫자부, 단위). 숫자부 끝 쉼표는 문장부호라 뗀다."""
    num = m.group(1).rstrip(",")
    unit = m.group(2)
    if m.group(1) != num:  # 쉼표를 뗐다면 단위는 숫자에 붙은 게 아니다
        return num, num, None
    return m.group(0).strip(), num, unit


def _decimals(num_part: str) -> int:
    return len(num_part.split(".")[1]) if "." in num_part else 0


def _tokens(text: str) -> list[tuple[str, float, str, str | None]]:
    """(원문 토큰, 정규화 값, 숫자부, 단위). 단위 없는 정수 ≤10과 연도는 버린다."""
    out = []
    for m in _NUMBER_RE.finditer(text):
        raw, num, unit = _split_token(m)
        value = float(num.replace(",", ""))
        if unit is None and value.is_integer() and "." not in num:
            if value <= _SMALL_INT_MAX or int(value) in _YEAR_RANGE:
                continue
        out.append((raw, value * _UNIT_MULT.get(unit, 1), num, unit))
    return out


def extract_numbers(text: str) -> list[tuple[str, float]]:
    """(원문 토큰, 정규화 값). 억·만 등은 배수를 곱하고 %·퍼센트는 값 그대로 둔다."""
    return [(raw, value) for raw, value, _, _ in _tokens(text)]


def fact_numbers(facts: object) -> list[float]:
    """facts JSON을 재귀로 돌며 숫자(bool 제외)와 문자열 안의 숫자를 모은다."""
    if isinstance(facts, bool):
        return []
    if isinstance(facts, (int, float)):
        return [float(facts)]
    if isinstance(facts, str):
        return [v for _, v in extract_numbers(facts)]
    if isinstance(facts, dict):
        return [n for v in facts.values() for n in fact_numbers(v)]
    if isinstance(facts, (list, tuple)):
        return [n for v in facts for n in fact_numbers(v)]
    return []


# ── 숫자 대조 ──────────────────────────────────────────────

def _token_matches(num_part: str, unit: str | None, facts_values: list[float]) -> bool:
    """보고서 토큰 하나가 facts 값 중 하나와 맞는가.

    규칙(오탐 '지어냄'을 줄이는 쪽으로 관대하게):
    - 비교는 보고서 토큰의 표시 소수 자릿수 d 로 반올림한 값끼리: |a-b| <= 0.5*10**-d.
    - 단위 토큰(억·만 등)은 facts 값을 배수로 나눈 값(f/배수)이 숫자부와 맞으면 일치
      (facts 312,000,000 ↔ "3.1억", facts 2,500,000 ↔ "250만").
    - 퍼센트 토큰은 facts 값 f 와 f*100(비율→퍼센트) 둘 다 후보.
    - 단위 없는 토큰은 f 그대로만 비교.
    """
    d = _decimals(num_part)
    tol = 0.5 * 10 ** (-d) + 1e-9
    shown = float(num_part.replace(",", ""))
    if unit in _PERCENT_UNITS:
        candidates = lambda f: (f, f * 100)  # noqa: E731
    elif unit in _UNIT_MULT:
        candidates = lambda f: (f / _UNIT_MULT[unit],)  # noqa: E731
    else:
        candidates = lambda f: (f,)  # noqa: E731
    return any(abs(c - shown) <= tol for f in facts_values for c in candidates(f))


def unmatched_numbers(report_md: str, facts: dict) -> list[str]:
    """보고서 숫자 중 facts의 어떤 값과도 맞지 않는 토큰(중복 제거, 등장 순서)."""
    facts_values = fact_numbers(facts)
    out: list[str] = []
    for raw, _, num, unit in _tokens(report_md):
        if raw not in out and not _token_matches(num, unit, facts_values):
            out.append(raw)
    return out


# ── 판정 일치 ──────────────────────────────────────────────

def verdict_matches(verdict_section_md: str, verdict_facts: dict) -> bool:
    """판정 절이 facts 판정과 같은 라벨만 말하는가. 자료가 없으면 단정 라벨이 없어야 한다."""
    if not verdict_facts.get("available"):
        return not any(label in verdict_section_md for label in _ASSERTIVE_LABELS)
    expected = VERDICT_LABELS.get(verdict_facts.get("verdict_code"))
    if expected is None or expected not in verdict_section_md:
        return False
    return not any(l != expected and l in verdict_section_md for l in VERDICT_LABELS.values())


# ── LLM 작성 절 ────────────────────────────────────────────

def llm_sections(deltas: dict[str, str], fallbacks: dict[str, str]) -> set[str]:
    """본문이 비어 있지 않고 폴백 문구와 다른 절 = LLM이 쓴 절."""
    return {
        key for key, body in deltas.items()
        if body.strip() and body.strip() != fallbacks.get(key, "").strip()
    }


# ── 블라인드 판정자 묶음 ───────────────────────────────────

def judge_packets(
    scenario_id: str, facts: dict, reports: dict[str, str], seed: int,
) -> tuple[str, dict[str, str]]:
    """모델명을 A·B… 로 가린 판정자용 마크다운과 {가린 이름: 모델명}. 순서는 시드로 결정적."""
    models = sorted(reports)
    random.Random(f"{seed}:{scenario_id}").shuffle(models)
    mapping = {chr(ord("A") + i): model for i, model in enumerate(models)}
    facts_json = json.dumps(facts, ensure_ascii=False, indent=1)[:_FACTS_JSON_LIMIT]
    parts = [f"# 시나리오 {scenario_id}", "", "## 사실 묶음(요약)", "```json", facts_json, "```"]
    for blind, model in mapping.items():
        parts += ["", f"## 리포트 {blind}", reports[model]]
    return "\n".join(parts) + "\n", mapping
