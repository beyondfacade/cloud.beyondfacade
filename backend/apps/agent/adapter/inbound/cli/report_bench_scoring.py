"""리포트 벤치 채점 — 순수 로직(DB·네트워크 없음, 결정적).

숫자 지어내기 대조, 판정 일치, LLM 작성 절 판별, 블라인드 판정자 묶음.
v0.68.0: 코드 절 자동 검사(범위 없는 숫자 줄·이유 빠진 자료 부족 자리)와 해석(answer) 판정 묶음.
"""

from __future__ import annotations

import difflib
import json
import random
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from itertools import combinations
from statistics import mean

from apps.agent.domain.services.report_guards import stated_grades
from apps.agent.domain.services.report_guards import verdict_matches, verdict_states_grade  # noqa: F401 — 벤치가 이 모듈 이름으로 쓴다
from apps.agent.domain.services.section_stream import concat_sections

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
RUBRIC_PATH = "data/eval/report_judge_rubric.md"  # 리포지토리 루트 기준
ANSWER_RUBRIC_PATH = "data/eval/report_answer_rubric.md"  # 해석 단락 판정 기준(v0.68.0)
FACTS_DIR = "data/eval/report_facts"


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

# 동의어 표·대조 규칙은 운영 가드와 같은 단일 원천(domain/services/report_guards.py)을 쓴다.


# ── 일관성(같은 모델·같은 시나리오의 반복 회차끼리) ─────────

def _by_scenario(runs: list[dict]) -> list[list[dict]]:
    """시나리오별 회차 묶음 — 회차가 하나뿐인 시나리오는 비교할 쌍이 없으니 뺀다."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        groups[r["id"]].append(r)
    return [sorted(g, key=lambda r: r["rep"]) for g in groups.values() if len(g) > 1]


def _pairwise(runs: list[dict], similarity: Callable[[dict, dict], float]) -> float | None:
    """회차 쌍별 유사도의 평균(전 시나리오의 쌍을 한데 모아)."""
    values = [similarity(a, b) for group in _by_scenario(runs) for a, b in combinations(group, 2)]
    return mean(values) if values else None


def _text(r: dict) -> str:
    """화면 본문 — 가드 후 절을 계약 순서로 잇는다(빈 절은 뺀다)."""
    return concat_sections((k, v) for k, v in r["sections"].items() if v)


def _numbers(r: dict) -> set[float]:
    return {value for _, value in extract_numbers(_text(r))}


def _alt_grades(r: dict) -> Counter:
    """대안 절 줄마다 쓴 등급(동의어 단일 원천으로 그룹화)의 다중집합 — 같은 대안에 같은 등급을 붙였는가."""
    lines = (r["sections"].get("alternatives") or "").splitlines()
    return Counter(group for line in lines for group in stated_grades(line))


def _outcome(r: dict) -> tuple[bool, bool, bool]:
    return r["complete"], r["verdict_ok"], bool(r["unmatched"])


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


def consistency_outcome(runs: list[dict]) -> float | None:
    """시나리오별로 모든 회차의 (완주, 판정 모순 없음, 지어낸 숫자 여부)가 같으면 1 — 시나리오 평균."""
    groups = _by_scenario(runs)
    if not groups:
        return None
    return mean(float(len({_outcome(r) for r in g}) == 1) for g in groups)


def consistency_numbers(runs: list[dict]) -> float | None:
    """회차 쌍별 리포트 전체 숫자 집합(지어내기 대조와 같은 토큰화)의 Jaccard 평균."""
    return _pairwise(runs, lambda a, b: _jaccard(_numbers(a), _numbers(b)))


def consistency_text(runs: list[dict]) -> float | None:
    """회차 쌍별 화면 본문 `SequenceMatcher.ratio()` 평균."""
    return _pairwise(runs, lambda a, b: difflib.SequenceMatcher(None, _text(a), _text(b)).ratio())


def consistency_alt_grades(runs: list[dict]) -> float | None:
    """회차 쌍별 대안 절 등급 다중집합이 같은 비율."""
    return _pairwise(runs, lambda a, b: float(_alt_grades(a) == _alt_grades(b)))


def consistency(runs: list[dict]) -> dict | None:
    """일관성 네 지표 묶음 — 비교할 시나리오가 없으면 None."""
    scenarios = len(_by_scenario(runs))
    if not scenarios:
        return None
    return {"outcome": consistency_outcome(runs), "numbers": consistency_numbers(runs),
            "text": consistency_text(runs), "alt_grades": consistency_alt_grades(runs), "scenarios": scenarios}


# ── LLM 작성 절 ────────────────────────────────────────────

def llm_sections(deltas: dict[str, str], fallbacks: dict[str, str]) -> set[str]:
    """본문이 비어 있지 않고 폴백 문구와 다른 절 = LLM이 쓴 절."""
    return {
        key for key, body in deltas.items()
        if body.strip() and body.strip() != fallbacks.get(key, "").strip()
    }


# ── 코드 절 자동 검사 (설계서 2026-10-05-report-code-first §7) ──

# 줄에 이 낱말이나 동·업종 이름이 있으면 숫자에 범위가 붙은 것으로 본다
SCOPE_WORDS = ("서울", "전국", "동 전체", "업종 무관", "최근")
_QUOTED = re.compile(r"「[^」]*」")  # 공고 제목 원문 — 제목 속 숫자는 주장이 아니다


def unscoped_number_lines(markdown: str, scope_words: Iterable[str], names: Iterable[str] = ()) -> list[str]:
    """사실값 숫자가 있는데 범위 낱말이 하나도 없는 줄.

    숫자 토큰은 지어내기 대조와 같은 규칙(`_tokens` — 단위 없는 10 이하 정수·연도는 버린다)이다.
    공고 제목(「」)과 이름(숫자가 든 동 이름 "상계3.4동")은 숫자로 세지 않는다.
    """
    scope, names = tuple(scope_words), tuple(names)
    out: list[str] = []
    for line in markdown.splitlines():
        text = _QUOTED.sub("", line)
        for name in names:
            text = text.replace(name, "")
        if _tokens(text) and not any(word in line for word in scope):
            out.append(line)
    return out


# 사실 키 → 그 자료가 없을 때 이유를 적어야 하는 절
_MISSING_SECTIONS = {
    "verdict": "verdict", "alternatives": "alternatives", "metrics_history": "reasons", "shocks": "reasons",
    "analogs": "analogs", "hour_gap": "conditions", "profile": "conditions", "commerce_change": "conditions",
    "funding_candidates": "funding",
}


def missing_data_gaps(facts: dict, sections: dict[str, str]) -> list[str]:
    """자료가 없는 자리(available false·표본 부족 신호)인데 해당 절에 그 이유가 그대로 적히지 않은 항목.

    이유를 적는 자리는 코드가 그 줄만 쓴다 — 추정 문장이 끼어들 틈이 없다(report_sections 단위 테스트가 고정).
    이유 뒤 ": 동코드 × 업종 id" 같은 내부 코드는 화면에 쓰지 않으므로(report_sections `_hours`) 콜론 앞까지만 대조한다.
    """
    gaps = [
        key for key, section in _MISSING_SECTIONS.items()
        if isinstance(value := facts.get(key), dict) and value.get("available") is False
        and (value.get("reason") or "").split(":")[0].strip() not in sections[section]
    ]
    signals = (facts.get("verdict") or {}).get("signals") or []
    return gaps + [
        f"signal:{s.get('key')}" for s in signals
        if s.get("level") == "unavailable" and (s.get("evidence") or "") not in sections["reasons"]
    ]


# ── 블라인드 판정자 묶음 ───────────────────────────────────

def judge_packets(
    scenario_id: str, facts: dict, reports: dict[str, str], seed: int,
) -> tuple[str, dict[str, str]]:
    """모델명을 A·B… 로 가린 판정자용 마크다운과 {가린 이름: 모델명}. 순서는 시드로 결정적."""
    models = sorted(reports)
    random.Random(f"{seed}:{scenario_id}").shuffle(models)
    mapping = {chr(ord("A") + i): model for i, model in enumerate(models)}
    facts_json = json.dumps(facts, ensure_ascii=False, indent=1)[:_FACTS_JSON_LIMIT]
    parts = [f"# 시나리오 {scenario_id}", "",
             f"채점 기준: `{RUBRIC_PATH}` · 전체 사실 묶음: `{FACTS_DIR}/{scenario_id}.json`", "",
             f"## 사실 묶음(요약 — 앞 {_FACTS_JSON_LIMIT:,}자에서 잘림, 대조는 위 전체 파일로)",
             "```json", facts_json, "```"]
    for blind, model in mapping.items():
        parts += ["", f"## 리포트 {blind}", reports[model]]
    return "\n".join(parts) + "\n", mapping


def answer_packets(
    scenario_id: str, question: str | None, body: str, answers: dict[str, str], seed: int,
) -> tuple[str, dict[str, str]]:
    """해석 판정 묶음 — 질문 + 코드가 쓴 본문 한 벌 + 모델명을 A·B…로 가린 해석들. 순서는 시드로 결정적."""
    models = sorted(answers)
    random.Random(f"{seed}:{scenario_id}").shuffle(models)
    mapping = {chr(ord("A") + i): model for i, model in enumerate(models)}
    parts = [f"# 시나리오 {scenario_id}", "", f"채점 기준: `{ANSWER_RUBRIC_PATH}`", "",
             f"질문: {question or '(없음 — 총평)'}", "",
             "## 리포트 본문 (코드가 사실로 쓴 6개 절 — 해석의 유일한 근거)", "", body]
    for blind, model in mapping.items():
        parts += ["", f"## 해석 {blind}", answers[model]]
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


def _no_grade(r: dict) -> str:
    return "-" if r.get("verdict_no_grade") is None else f"{r['verdict_no_grade']}/{r.get('n', '-')}"


def _report_row(r: dict) -> list[str]:
    return [r["model"], _cell(r, "vram_mib", "{:.0f}"), _cell(r, "quality", "{:.2f}"), _cell(r, "completion", "{:.2f}"),
            _cell(r, "verdict_match", "{:.2f}"), _no_grade(r), _cell(r, "fabrication", "{:.2f}"),
            _cell(r, "rule_violations"),
            _cell(r, "first_p95_ms", "{:.0f}"), _cell(r, "total_p95_ms", "{:.0f}"),
            _ox(r["gates"]["all"]), r.get("note", "")]


def _ratio(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def _consistency_lines(rows: list[dict]) -> list[str]:
    """반복 회차끼리의 일관성 — 같은 질문에 같은 답을 내는가. 계산된 행에만 싣는다."""
    measured = [r for r in rows if r.get("consistency")]
    if not measured:
        return []
    table = _table(
        ["모델", "온도/seed", "시나리오", "결과 일치", "숫자 Jaccard", "본문 유사도", "대안 등급 일치"],
        [[r["model"], r.get("sampling") or "-", str(r["consistency"]["scenarios"]),
          *(_ratio(r["consistency"][k]) for k in ("outcome", "numbers", "text", "alt_grades"))] for r in measured],
    )
    return ["", "## 일관성(반복 3회)", "",
            "같은 모델·같은 시나리오의 회차끼리 비교. 결과 일치 = (완주, 판정 모순 없음, 지어내기 여부)가 모든 회차에서 같은 "
            "시나리오 비율, 숫자 Jaccard·본문 유사도(화면 본문 SequenceMatcher)·대안 등급 일치 = 회차 쌍 평균.", "",
            *table]


def _guard_lines(rows: list[dict]) -> list[str]:
    """v0.67.0 코드 가드 개입 — 모델별 횟수와 가드 전 원문 지표. 개입 기록이 있는 결과에만 싣는다."""
    guarded = [r for r in rows if r.get("guard")]
    if not guarded:
        return []
    table = _table(
        ["모델", "판정 교체", "링크 제거", "태그 추가", "고지문", "원문 판정 모순 없음", "원문 지어내기"],
        [[r["model"], *(str(r["guard"].get(k, 0)) for k in
                        ("verdict_replaced", "links_stripped", "tags_added", "disclaimer_added")),
          f"{r['raw']['verdict_match']:.2f}", f"{r['raw']['fabrication']:.2f}"] for r in guarded],
    )
    return ["", "## 코드 가드 개입", "",
            "표의 지표는 화면 본문(가드 후) 기준이다. 아래는 모델별 가드 개입 횟수(전 회차 합)와 가드 전 원문 지표.", "",
            *table, "",
            "- 첫 글자 p95는 판정 절 전체를 붙드는 시간을 포함한다(판정 절은 끝날 때 한 번에 나간다) — "
            "2026-10-05 기준선의 첫 글자와 비교할 수 없다."]


def _intent_row(r: dict) -> list[str]:
    return [r["model"], _cell(r, "vram_mib", "{:.0f}"), _cell(r, "both", "{:.3f}"), _cell(r, "region", "{:.3f}"),
            _cell(r, "industry", "{:.3f}"), _cell(r, "budget", "{:.3f}"), _cell(r, "schema_rate", "{:.3f}"),
            _cell(r, "fabrication_rate", "{:.3f}"), _cell(r, "fabrication_any_null", "{:.3f}"),
            _cell(r, "p95_ms", "{:.0f}"), _ox(r["gates"]["all"])]


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


def _ci(ci: list[float] | None) -> str:
    """1위 − 이 모델(평균, 하한, 상한). 1위 자신은 '-'."""
    return "-" if ci is None else f"{ci[0]:+.2f} [{ci[1]:+.2f}, {ci[2]:+.2f}]"


def _cost_lines(cost: dict | None) -> list[str]:
    if not cost:
        return []
    price = cost["price_per_1m_usd"]
    return ["", "## 비용 (온라인 비교군)", "",
            f"- {cost['model']} 리포트 1건 평균 토큰(캐시 {cost['n']}건): 입력 {cost['mean_input_tokens']:,.0f} / "
            f"출력 {cost['mean_output_tokens']:,.0f}",
            f"- 단가 입력 ${price['input']:.2f} / 출력 ${price['output']:.2f} (1M 토큰당, 확인 {cost['checked']}, "
            f"{cost['source']}) → 리포트 1건 약 ${cost['usd_per_report']:.4f}"]


def _reference_lines(report: dict) -> list[str]:
    ref = report.get("reference")
    if not ref:
        return []
    lines = ["", "## 참고 순위 (게이트와 별개)", ""]
    if report.get("winner") is None:
        lines += ["엄격 게이트를 통과한 로컬 리포트 모델이 없어 아래는 참고용이며 채택 결정이 아니다.", ""]
    if ref.get("winner"):
        lines += [f"- 참고 1위(동률 시 VRAM 작은 쪽): **{ref['winner']}** — 동률 {{{', '.join(ref['tied'])}}}", ""]
    ci = ref.get("ci_vs_best", {})
    lines += _table(["순위", "모델", "품질", "1위 대비 차이 [95% 구간]", "VRAM(MiB)", "게이트 탈락"],
                    [[str(i), r["model"], _cell(r, "quality", "{:.2f}"), _ci(ci.get(r["model"])),
                      _cell(r, "vram_mib", "{:.0f}"), ", ".join(r["failed"]) or "-"]
                     for i, r in enumerate(ref["ranking"], 1)])
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
    lines += _table(["모델", "VRAM(MiB)", "품질", "완주", "판정 모순 없음", "판정 등급 생략", "지어내기", "규칙",
                     "첫 글자 p95(ms)", "완료 p95(ms)", "게이트", "비고"],
                    [_report_row(r) for r in results["report"]["rows"]])
    lines += ["", "## 의도 관문", ""]
    lines += _table(["모델", "VRAM(MiB)", "동시 정답", "지역", "업종", "예산", "스키마", "지어내기",
                     "지어내기(null 칸 전체, 참고)", "p95(ms)", "게이트"],
                    [_intent_row(r) for r in results["intent"]["rows"]])
    lines += ["", "## 판정", "", _verdict_line("리포트", results["report"]), _verdict_line("관문", results["intent"]),
              _residency_line(results.get("residency"))]
    lines += _reference_lines(results["report"])
    lines += _guard_lines(results["report"]["rows"])
    lines += _consistency_lines(results["report"]["rows"])
    lines += _cost_lines(results.get("cost"))
    lines += ["", "## 한계", "",
              "- 숫자 대조는 관대하게 맞춘다(프롬프트·도구 설명 숫자도 근거, 복합 금액 허용폭이 넓음) — 지어내기 비율은 하한이다. "
              "오탐도 있을 수 있다(불일치 목록으로 사람이 확인).",
              "- 품질 판정자도 LLM이다(모델명은 가렸지만 문체로 짐작할 수 있다).",
              "- 리포트 시나리오는 12건이라 표본이 작다.",
              "", "해설·결론·측정 메모는 [notes.md](notes.md)(수기, evaluate가 덮어쓰지 않음)."]
    return "\n".join(lines) + "\n"
