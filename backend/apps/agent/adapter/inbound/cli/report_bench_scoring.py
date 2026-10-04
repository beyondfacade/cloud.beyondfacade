"""리포트 벤치 채점 — 순수 로직(DB·네트워크 없음, 결정적).

숫자 지어내기 대조, 판정 일치, LLM 작성 절 판별, 블라인드 판정자 묶음.
"""

from __future__ import annotations

import json
import random
import re

_N = r"\d[\d,]*(?:\.\d+)?"
# 복합 금액("1억 2천만")을 먼저 한 토큰으로 잡고, 아니면 숫자+선택 단위.
_NUMBER_RE = re.compile(
    rf"(?:(?P<c1>{_N})\s*억\s*(?P<c2>{_N})\s*(?P<cu>천만|백만|만|천)"
    rf"|(?P<n>{_N})\s*(?P<u>%p|%|퍼센트|억|천만|백만|만|천)?)"
)
_UNIT_MULT = {"억": 1e8, "천만": 1e7, "백만": 1e6, "만": 1e4, "천": 1e3}
_PERCENT_UNITS = {"%", "%p", "퍼센트"}
_SMALL_INT_MAX = 10
_YEAR_RANGE = range(1990, 2101)
_NON_FACT_SUFFIXES = "대위"  # 연령대("20대")·순위("12위")는 사실값이 아니다
_EPS = 1e-6

VERDICT_LABELS = {"red": "비추천", "orange": "조건부", "clear": "경고 없음", "insufficient": "판정 보류"}

_FACTS_JSON_LIMIT = 3000


# ── 숫자 추출 ──────────────────────────────────────────────

def _num(text: str) -> float:
    return float(text.replace(",", ""))


def _decimals(num_part: str) -> int:
    return len(num_part.split(".")[1]) if "." in num_part else 0


def _tokens(text: str) -> list[tuple[str, float, float, str | None]]:
    """(원문 토큰, 정규화 값, 표시 정밀도의 절반 폭, 단위).

    - 숫자부 끝 쉼표는 문장부호라 뗀다(그러면 단위는 붙지 않은 것으로 본다).
    - 단위 없는 정수 ≤10, 연도(1990~2100), 뒤에 대·위가 붙은 정수는 버린다.
    - 복합 금액은 합산한 한 토큰이며 정밀도는 가장 작은 단위(예: 천만이면 0.5×1e7)다.
    """
    out = []
    for m in _NUMBER_RE.finditer(text):
        if m.group("c1") is not None:
            mult = _UNIT_MULT[m.group("cu")]
            value = _num(m.group("c1")) * 1e8 + _num(m.group("c2")) * mult
            half = 0.5 * 10 ** (-_decimals(m.group("c2"))) * mult
            out.append((m.group(0).strip(), value, half, "복합"))
            continue
        num, unit = m.group("n"), m.group("u")
        if num.endswith(","):
            num, unit = num.rstrip(","), None
            raw = num
        else:
            raw = m.group(0).strip()
        shown = _num(num)
        if unit is None and "." not in num:
            suffix = text[m.end():m.end() + 1]
            if shown <= _SMALL_INT_MAX or int(shown) in _YEAR_RANGE or (suffix and suffix in _NON_FACT_SUFFIXES):
                continue
        mult = _UNIT_MULT.get(unit, 1)
        out.append((raw, shown * mult, 0.5 * 10 ** (-_decimals(num)) * mult, unit))
    return out


def extract_numbers(text: str) -> list[tuple[str, float]]:
    """(원문 토큰, 정규화 값). 억·만 등은 배수를 곱하고 %·퍼센트는 값 그대로 둔다. 부호는 보지 않는다."""
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

def _token_matches(value: float, half: float, unit: str | None, facts_values: list[float]) -> bool:
    """보고서 토큰 하나가 facts 값 중 하나와 맞는가.

    규칙(오탐 '지어냄'을 줄이는 쪽으로 관대하게):
    - 부호는 비교하지 않는다(보고서는 "감소" 같은 말로 부호를 표현) — 양쪽 절댓값 비교.
    - 표시 정밀도의 절반 폭 안이면 일치: |fact − value| <= half
      (단위 토큰은 폭에 배수를 곱함: "3.1억" ↔ 312,000,000, "250만" ↔ 2,500,000).
    - 퍼센트 토큰(%·%p·퍼센트)은 facts 값 f 와 f*100(비율→퍼센트) 둘 다 후보.
    - 복합 금액("1억 2천만")은 가장 작은 단위 정밀도로 합산값 전체를 비교.
    """
    value = abs(value)
    for f in facts_values:
        candidates = (f, f * 100) if unit in _PERCENT_UNITS else (f,)
        if any(abs(abs(c) - value) <= half + _EPS for c in candidates):
            return True
    return False


def unmatched_numbers(report_md: str, facts: dict) -> list[str]:
    """보고서 숫자 중 facts의 어떤 값과도 맞지 않는 토큰(중복 제거, 등장 순서)."""
    facts_values = fact_numbers(facts)
    out: list[str] = []
    for raw, value, half, unit in _tokens(report_md):
        if raw not in out and not _token_matches(value, half, unit, facts_values):
            out.append(raw)
    return out


# ── 판정 일치 ──────────────────────────────────────────────

# 판정별 동의어 — 앞 두 개가 '핵심 라벨'(다른 등급 모순 검사용). 공백은 제거 후 비교.
_VERDICT_SYNONYMS = {
    "red": ("비추천", "빨강", "레드", "red"),
    "orange": ("조건부", "주황", "오렌지", "orange"),
    "clear": ("경고없", "경고가없", "위험신호가없", "clear"),
    "unavailable": ("판정없음", "판정보류", "보류", "판정할수없", "판정하지않"),
}
_CORE_COUNT = 2


def verdict_matches(verdict_section_md: str, verdict_facts: dict) -> bool:
    """판정 절이 facts 판정을 (동의어로라도) 말하고 다른 등급의 핵심 라벨은 없는가.

    자료가 없으면(available False) 비추천·조건부·경고 없음 계열 핵심 라벨이 없어야 한다.
    """
    text = re.sub(r"\s+", "", verdict_section_md).lower()
    code = verdict_facts.get("verdict_code") if verdict_facts.get("available") else "unavailable"
    if code == "insufficient":
        code = "unavailable"
    if code not in _VERDICT_SYNONYMS:
        return False
    foreign_core = [w for k, ws in _VERDICT_SYNONYMS.items() if k not in (code, "unavailable")
                    for w in ws[:_CORE_COUNT]]
    if any(w in text for w in foreign_core):
        return False
    return any(w in text for w in _VERDICT_SYNONYMS[code])


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
