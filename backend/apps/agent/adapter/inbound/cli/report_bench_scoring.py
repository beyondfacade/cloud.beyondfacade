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

# 판정 그룹별 동의어(공백 제거·소문자 기준으로 비교). 그룹 하나가 한 등급의 표현이다.
_VERDICT_SYNONYMS = {
    "red": ("비추천", "빨강", "빨간", "레드", "red", "적색"),
    "orange": ("조건부", "주황", "오렌지", "orange", "'주의' 등급", "주의 등급"),
    "clear": ("경고 없", "경고가 없", "위험 신호가 없", "위험 신호도 켜지지 않", "clear"),
    "unavailable": ("판정 없음", "판정 보류", "판정할 수 없", "판정하지 않", "판정을 내리지 않", "insufficient"),
}
_VERDICT_GROUP = {"insufficient": "unavailable"}  # verdict_code → 동의어 그룹(나머지는 코드가 곧 그룹)


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


_SQUASHED_SYNONYMS = {group: tuple(_squash(w) for w in words) for group, words in _VERDICT_SYNONYMS.items()}


def verdict_matches(verdict_section_md: str, verdict_facts: dict) -> bool:
    """판정 절이 facts 판정과 모순되지 않는가 — 다른 등급의 동의어를 단정하지 않으면 통과.

    등급 말을 아예 안 쓴 절(생략)은 모순이 아니다. 판정 자료가 없으면(available False)
    unavailable 그룹이 기대 등급이며, 비추천·조건부·경고 없음 계열 말은 모두 모순이다.
    """
    text = _squash(verdict_section_md)
    code = verdict_facts.get("verdict_code") if verdict_facts.get("available") else "unavailable"
    group = _VERDICT_GROUP.get(code, code)
    if group not in _SQUASHED_SYNONYMS:
        return False
    return not any(w in text for g, words in _SQUASHED_SYNONYMS.items() if g != group for w in words)


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


# ── 판정자에게 보이는 본문의 모델명 가리기 ─────────────────

_MODEL_NAMES = ("LG AI", "LG", "gemma", "qwen", "kanana", "exaone", "gemini", "Kakao", "카카오",
                "Google", "구글", "Alibaba", "알리바바")
# 영문 이름은 앞뒤가 영문자가 아닐 때만(algorithm 같은 단어 보호), 뒤에 붙은 버전 꼬리("4:12b")까지 함께 가린다.
_MASK_RE = re.compile(
    r"(?<![A-Za-z])(?:" + "|".join(re.escape(n) for n in sorted(_MODEL_NAMES, key=len, reverse=True)) + r")"
    r"(?![A-Za-z])(?:[-:]?\d[A-Za-z0-9.:\-]*(?<![.:\-]))?",
    re.IGNORECASE,
)


def mask_model_names(text: str) -> str:
    """판정자가 모델·회사를 짐작하지 못하게 이름을 [모델]로 바꾼다(대소문자 무시)."""
    return _MASK_RE.sub("[모델]", text)


# ── 게이트 ─────────────────────────────────────────────────

REPORT_LIMITS = {"completion": 0.95, "verdict_match": 1.0, "fabrication": 0.05,
                 "first_p95_ms": 5000, "total_p95_ms": 60000}
INTENT_LIMITS = {"schema_rate": 0.98, "fabrication_rate": 0.05, "p95_ms": 3000}


def report_gates(score: dict, latency: dict) -> dict[str, bool]:
    return {
        "completion": score["completion"] >= REPORT_LIMITS["completion"],
        "verdict_match": score["verdict_match"] >= REPORT_LIMITS["verdict_match"],
        "fabrication": score["fabrication"] <= REPORT_LIMITS["fabrication"],
        "rules": score["rule_violations"] == 0,
        "latency": latency["first_p95_ms"] <= REPORT_LIMITS["first_p95_ms"]
        and latency["total_p95_ms"] <= REPORT_LIMITS["total_p95_ms"],
    }


def intent_gates(summary: dict) -> dict[str, bool]:
    return {
        "schema": summary["schema_rate"] >= INTENT_LIMITS["schema_rate"],
        "fabrication": summary["fabrication_rate"] <= INTENT_LIMITS["fabrication_rate"],
        "latency": summary["p95_ms"] <= INTENT_LIMITS["p95_ms"],
    }


# ── 결과 보고서 ────────────────────────────────────────────

def _cell(row: dict, key: str, fmt: str = "{}") -> str:
    value = row.get(key)
    return "-" if value is None else fmt.format(value)


def _ox(flag: bool) -> str:
    return "O" if flag else "X"


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    return lines + ["| " + " | ".join(r) + " |" for r in rows]


def _report_row(r: dict) -> list[str]:
    return [r["model"], _cell(r, "vram_mib", "{:.0f}"), _cell(r, "quality", "{:.2f}"), _cell(r, "completion", "{:.2f}"),
            _cell(r, "verdict_match", "{:.2f}"), _cell(r, "fabrication", "{:.2f}"), _cell(r, "rule_violations"),
            _cell(r, "first_p95_ms", "{:.0f}"), _cell(r, "total_p95_ms", "{:.0f}"),
            _ox(r["gates"]["all"]), r.get("note", "")]


def _intent_row(r: dict) -> list[str]:
    return [r["model"], _cell(r, "vram_mib", "{:.0f}"), _cell(r, "both", "{:.3f}"), _cell(r, "region", "{:.3f}"),
            _cell(r, "industry", "{:.3f}"), _cell(r, "budget", "{:.3f}"), _cell(r, "schema_rate", "{:.3f}"),
            _cell(r, "fabrication_rate", "{:.3f}"), _cell(r, "p95_ms", "{:.0f}"), _ox(r["gates"]["all"])]


# 판정자 위반 문장 → 유형. 위에서부터 첫 일치, 아무것도 안 맞으면 마지막 "기타".
VIOLATION_TYPES = ("신뢰 등급 표기", "금융", "재난기", "차별", "기타")
_VIOLATION_KEYWORDS = {
    "신뢰 등급 표기": ("신뢰", "표기", "확인된 사실", "참고 신호", "태그"),
    "금융": ("금융", "대출", "은행", "금리", "한도", "상품", "예상치"),
    "재난기": ("재난", "2020", "2021", "2022", "코로나", "팬데믹"),
    "차별": ("차별", "외국인", "혐오", "비하"),
}


def classify_violation(text: str) -> str:
    return next((kind for kind, words in _VIOLATION_KEYWORDS.items() if any(w in text for w in words)), "기타")


def _reference_lines(report: dict) -> list[str]:
    ref = report.get("reference")
    if not ref:
        return []
    lines = ["", "## 참고 순위 (게이트와 별개)", ""]
    if report.get("winner") is None:
        lines += ["엄격 게이트를 통과한 로컬 리포트 모델이 없어 아래는 참고용이며 채택 결정이 아니다.", ""]
    if ref.get("winner"):
        lines += [f"- 참고 1위(동률 시 VRAM 작은 쪽): **{ref['winner']}** — 동률 {{{', '.join(ref['tied'])}}}", ""]
    lines += _table(["순위", "모델", "품질", "VRAM(MiB)", "게이트 탈락"],
                    [[str(i), r["model"], _cell(r, "quality", "{:.2f}"), _cell(r, "vram_mib", "{:.0f}"),
                      ", ".join(r["failed"]) or "-"] for i, r in enumerate(ref["ranking"], 1)])
    lines += ["", "### 판정자 위반 유형 내역", ""]
    lines += _table(["모델", *VIOLATION_TYPES],
                    [[m, *(str(counts.get(k, 0)) for k in VIOLATION_TYPES)] for m, counts in ref["violations"].items()])
    return lines


def _verdict_line(role: str, block: dict) -> str:
    if block.get("winner") is None:
        reasons = "; ".join(f"{r['model']}({r['excluded']})" for r in block.get("rows", []) if r.get("excluded"))
        return f"- {role}: **없음** — {reasons or '게이트를 통과한 로컬 모델이 없다'}"
    return f"- {role}: **{block['winner']}** — 동률 {', '.join(block['tied'])}"


def _residency_line(residency: dict | None) -> str:
    if not residency or residency.get("ok") is None:
        return "- 동시 상주: 미측정"
    return f"- 동시 상주: {_ox(residency['ok'])} ({residency.get('used_mib', '-')} MiB)"


def render_llm_report(results: dict) -> str:
    """역할별 표·판정·한계 마크다운. 온라인 행도 표에는 싣지만 판정 대상이 아니다(note로 표시)."""
    lines = [f"# LLM 모델 평가 결과 ({results['date']})", "", "## 리포트 작성", ""]
    lines += _table(["모델", "VRAM(MiB)", "품질", "완주", "판정 일치", "지어내기", "규칙", "첫 글자 p95(ms)",
                     "완료 p95(ms)", "게이트", "비고"], [_report_row(r) for r in results["report"]["rows"]])
    lines += ["", "## 의도 관문", ""]
    lines += _table(["모델", "VRAM(MiB)", "동시 정답", "지역", "업종", "예산", "스키마", "지어내기", "p95(ms)", "게이트"],
                    [_intent_row(r) for r in results["intent"]["rows"]])
    lines += ["", "## 판정", "", _verdict_line("리포트", results["report"]), _verdict_line("관문", results["intent"]),
              _residency_line(results.get("residency"))]
    lines += _reference_lines(results["report"])
    lines += ["", "## 한계", "",
              "- 숫자 대조는 오탐이 있을 수 있다(불일치 목록으로 사람이 확인).",
              "- 품질 판정자도 LLM이다(모델명은 가렸지만 문체로 짐작할 수 있다).",
              "- 리포트 시나리오는 12건이라 표본이 작다."]
    return "\n".join(lines) + "\n"
