# 질문 유형별 직접 답 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 질문이 있는 리포트에서 해석 맨 위 직접 답(첫 문장)과 근거 줄을 코드가 질문 유형에 맞춰 쓰고, LLM은 그 아래 해석 2~3문장만 쓰게 한다.

**Architecture:** agent BC 도메인에 순수 모듈 2개(`question_topic` 키워드 분류, `question_answer` 유형별 Strategy)를 더하고, `AnalysisInteractor`가 새 SSE 절 `answer_lead`를 6개 절과 함께 즉시 내보낸다. facts에 자금 계획 프리필(`finance`)과 질문 속 예산을 싣는다. 본문 "그래도 한다면" 절에 거주민·뉴스 줄을 더한다.

**Tech Stack:** Python 3.14, FastAPI, pytest (backend `.venv`), Next.js + Vitest (frontend, Codex 위임)

**Spec:** `docs/superpowers/specs/2026-10-05-question-answer-design.md`

## Global Constraints

- 작업 디렉터리: `/home/kimchungsik/projects/cloud.beyondfacade/.worktrees/question-answer` (git worktree, 브랜치 `feat/question-answer`). 이 밖의 경로를 수정하지 않는다.
- 백엔드 테스트: `cd backend && .venv/bin/python -m pytest -q` (기준선 1224 통과). 테스트 파일은 `backend/tests/` 평면 배치, 테스트 이름은 한국어 서술문(`def test_…():`).
- `domain/`·`app/use_cases/`는 FastAPI·SQLAlchemy·어댑터·타 BC를 import하지 않는다. 타 BC 접근은 `adapter/outbound/gateways/*` 안에서만.
- 코드가 쓰는 문장 규칙(설계서 §5): 숫자가 든 줄에는 동 이름·업종 이름·"서울"·"전국" 중 하나를 넣는다(벤치 `sections-check`의 범위 검사). 자료가 없으면 `missing(이유)`("자료 부족 — 이유"). 태그는 정형 `[확인된 사실]`, 뉴스 `[참고 신호]`.
- 분기 디스패치는 if/elif 대신 dict·Strategy(CLAUDE.md §5).
- 과도한 테스트 금지 — 요청된 동작과 확인된 위험만.
- 커밋 메시지 끝: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- 버전: backend v0.69.0(Task 7에서 `backend/docs/backend_ver_log.md` 기록), frontend v0.54.0(Task 8).

---

### Task 1: 질문 유형 분류기

**Files:**
- Create: `backend/apps/agent/domain/services/question_topic.py`
- Test: `backend/tests/test_question_topic.py`

**Interfaces:**
- Produces: `QuestionTopic(kind: str, detail: str | None = None)` frozen dataclass; `classify(question: str | None) -> QuestionTopic | None`. kind ∈ `loan·budget·hours·competition·customers·covid·general`. detail: hours → `lunch·evening·night·morning·weekend`, customers → `"foreign"`(외국인·중국인) 또는 None.

- [ ] **Step 1: 실패하는 테스트**

```python
"""question_topic — 질문 → 유형 (키워드 규칙, 결정적)."""

import json
from pathlib import Path

import pytest

from apps.agent.domain.services.question_topic import QuestionTopic, classify

_SCENARIOS = Path(__file__).resolve().parents[2] / "data/eval/report_scenarios_150.jsonl"

# 평가셋 질문 원문 → 기대 유형. 평가셋의 모든 질문이 여기 있어야 한다(73/73).
_EXPECTED = {
    "은행 대출 받아서 차려도 될까요?": QuestionTopic("loan"),
    "대출 끼고 시작해도 될까요?": QuestionTopic("loan"),
    "은행 대출로 보증금이랑 인테리어 비용을 마련하려는데 괜찮을까요?": QuestionTopic("loan"),
    "모자란 돈은 대출로 메우려는데 무리일까요?": QuestionTopic("loan"),
    "외국인이 많은 동네인데 괜찮을까요?": QuestionTopic("customers", "foreign"),
    "중국인 손님이 많다던데 괜찮을까요?": QuestionTopic("customers", "foreign"),
    "외국인 주민이 많이 사는 동네라던데 장사가 될까요?": QuestionTopic("customers", "foreign"),
    "어르신들이 많이 사는 동네라던데 괜찮을까요?": QuestionTopic("customers"),
    "점심시간 손님을 주로 보려는데 이 동네 괜찮을까요?": QuestionTopic("hours", "lunch"),
    "밤늦게까지 문을 열 생각인데 여기 괜찮을까요?": QuestionTopic("hours", "night"),
    "주말 손님 위주로 생각하고 있는데 어떨까요?": QuestionTopic("hours", "weekend"),
    "코로나 때 폐업 많았던 동네라던데 괜찮을까요?": QuestionTopic("covid"),
    "코로나 시기에 가게들이 많이 문 닫은 곳이라던데 지금은 어떨까요?": QuestionTopic("covid"),
}
# 업종 이름·금액만 바뀌는 질문 틀 — 정규식 대신 접두·접미로 맞춘다
_PATTERNS = (
    (lambda q: q.startswith("보증금 포함"), QuestionTopic("budget")),
    (lambda q: q.startswith("모아 둔 돈이"), QuestionTopic("budget")),
    (lambda q: q.startswith("저녁 장사 위주로"), QuestionTopic("hours", "evening")),
    (lambda q: "이미 많은 것 같은데" in q or "벌써 여러 곳" in q or q.startswith("경쟁 가게가"), QuestionTopic("competition")),
    (lambda q: q.startswith("여기서") and q.endswith("차려도 괜찮을까요?"), QuestionTopic("general")),
    (lambda q: q.startswith("이 동네에") and q.endswith("열면 어떨까요?"), QuestionTopic("general")),
    (lambda q: q.endswith("창업을 생각 중인데 여기 괜찮은 자리일까요?"), QuestionTopic("general")),
)


def _expected(question: str) -> QuestionTopic:
    if question in _EXPECTED:
        return _EXPECTED[question]
    return next(topic for match, topic in _PATTERNS if match(question))


def test_평가셋_질문_전부를_기대_유형으로_분류한다():
    questions = [json.loads(line)["question"] for line in _SCENARIOS.read_text(encoding="utf-8").splitlines() if line.strip()]
    questions = [q for q in questions if q]

    assert len(questions) == 73
    assert [classify(q) for q in questions] == [_expected(q) for q in questions]


@pytest.mark.parametrize("question", [None, "", "   "])
def test_질문이_없으면_유형도_없다(question):
    assert classify(question) is None


def test_여러_유형이_섞이면_대출이_먼저다():
    assert classify("대출로 1억 원 마련해서 저녁 장사 하려는데요") == QuestionTopic("loan")
```

- [ ] **Step 2: 실패 확인** — `cd backend && .venv/bin/python -m pytest tests/test_question_topic.py -q` → ModuleNotFoundError.

- [ ] **Step 3: 구현**

```python
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
```

- [ ] **Step 4: 통과 확인** — 같은 명령 → 5 passed.
- [ ] **Step 5: 커밋** — `git add backend/apps/agent/domain/services/question_topic.py backend/tests/test_question_topic.py && git commit -m "backend: 질문 유형 분류기(키워드 규칙)"` (+ Co-Authored-By 줄)

---

### Task 2: 직접 답 첫 문장 + 일반·예산·대출 근거

**Files:**
- Modify: `backend/apps/agent/domain/services/report_sections.py` (공용 이름 공개 — 이름만 바꾼다)
- Create: `backend/apps/agent/domain/services/question_answer.py`
- Test: `backend/tests/test_question_answer.py`

**Interfaces:**
- Consumes: Task 1 `QuestionTopic`.
- Produces (report_sections 공개 이름, 이 파일 안 참조만 바뀐다): `subject_names(facts) -> tuple[str, str]`(옛 `_names`), `quarter_label(yq)`(옛 `_quarter`), `topic_particle(word)`(옛 `_topic`), `missing_reason(value)`(옛 `_missing_reason`), `current_year(facts)`(옛 `_current_year`), `VERDICT_LABELS`, `SIGNAL_LABELS`, `DISASTER_NOTE`.
- Produces (question_answer): `TopicAnswer`(ABC: `head`, `tail`, `lead`, 추상 `evidence`), `answer_lead(facts: dict, topic: QuestionTopic) -> str`, `won(amount: int) -> str`, `revenue_line(facts) -> str`, `rent_line(facts) -> str`, `loan_rate_line(facts) -> str`, 상수 `BUDGET_GAP`, `LOAN_NOTE`, `BAND_NAMES`, 그리고 Task 4가 채울 `_ANSWERS: dict[str, TopicAnswer]`.
- `facts["finance"]` 모양(Task 5가 채운다): `{"available": True, "expected_monthly_revenue": {value, unit, basis, caveat}, "rent_per_m2": {...}, "loan_rate": {...}}` 또는 `{"available": False, "reason": "..."}`. basis 예: 매출 `{"year_quarter": "20254", "store_count": 13, ...}`, 임대료 `{"region_path": "서울>기타", "period": "2026Q2", ...}`, 금리 `{"period": "202608", "rate_pct": 4.05, ...}`. 값 단위: 매출 원/월, 임대료 천원/㎡/월, 금리 비율(0.0405).

- [ ] **Step 1: report_sections 이름 공개** (동작 변화 없음)

```bash
cd backend && sed -i -E \
  -e 's/\b_names\(/subject_names(/g' \
  -e 's/\b_quarter\(/quarter_label(/g' \
  -e 's/\b_topic\(/topic_particle(/g' \
  -e 's/\b_missing_reason\(/missing_reason(/g' \
  -e 's/\b_current_year\(/current_year(/g' \
  -e 's/\b_VERDICT_LABELS\b/VERDICT_LABELS/g' \
  -e 's/\b_SIGNAL_LABELS\b/SIGNAL_LABELS/g' \
  -e 's/\b_DISASTER_NOTE\b/DISASTER_NOTE/g' \
  apps/agent/domain/services/report_sections.py
grep -n "_MISSING_SIGNAL_LABELS\|def subject_names\|def quarter_label" apps/agent/domain/services/report_sections.py
.venv/bin/python -m pytest -q tests/test_report_sections.py tests/test_agent_loop.py
```
Expected: `_MISSING_SIGNAL_LABELS`는 그대로(앞 글자가 단어 문자라 `\b`가 안 걸린다), 테스트 전부 통과. 다른 모듈이 옛 이름을 import하지 않는지 `grep -rn "report_sections import" apps tests`로 확인.

- [ ] **Step 2: 실패하는 테스트**

```python
"""question_answer — 질문 유형별 직접 답(첫 문장)과 근거 줄 (facts만, LLM·DB 없음)."""

import json
from pathlib import Path

from apps.agent.domain.services.question_answer import BUDGET_GAP, LOAN_NOTE, answer_lead, won
from apps.agent.domain.services.question_topic import QuestionTopic

# 평가셋 고정 facts(e001 송정동 한식, 판정 red — 순유출·조기 폐업 strong, 포화 off)
_BASE = json.loads(
    (Path(__file__).resolve().parents[2] / "data/eval/report_facts_150/e001.json").read_text(encoding="utf-8")
)
_FINANCE = {
    "available": True,
    "expected_monthly_revenue": {"value": 4325694.0, "unit": "원/월", "caveat": "편차가 큽니다.",
                                 "basis": {"year_quarter": "20254", "store_count": 13}},
    "rent_per_m2": {"value": 49.33, "unit": "천원/㎡/월", "caveat": "행정동 단위 임대료 자료가 없어 권역 평균입니다.",
                    "basis": {"region_path": "서울>기타", "period": "2026Q2"}},
    "loan_rate": {"value": 0.0405, "unit": "비율", "caveat": "공시 평균 금리입니다.",
                  "basis": {"period": "202608", "rate_pct": 4.05}},
}


def _facts(**overrides) -> dict:
    return {**_BASE, "finance": _FINANCE, **overrides}


def _verdict(code: str) -> dict:
    return {**_BASE["verdict"], "verdict_code": code}


def test_비추천은_권하지_않는다와_켜진_신호를_첫_문장에_쓴다():
    lead = answer_lead(_facts(), QuestionTopic("general")).split("\n")[0]
    assert lead == "[확인된 사실] 송정동 한식은 권하지 않습니다 — 켜진 경고 신호 2개(순유출, 조기 폐업)."


def test_조건부는_먼저_확인할_신호를_쓴다():
    lead = answer_lead(_facts(verdict=_verdict("orange")), QuestionTopic("general")).split("\n")[0]
    assert lead == "[확인된 사실] 송정동 한식은 조건부입니다 — 순유출, 조기 폐업을 먼저 확인해야 합니다."


def test_경고_없음은_장사가_된다는_근거가_아니라고_쓴다():
    lead = answer_lead(_facts(verdict=_verdict("clear")), QuestionTopic("general")).split("\n")[0]
    assert lead == "[확인된 사실] 송정동 한식은 경고 신호가 없습니다 — 다만 이것이 장사가 된다는 근거는 아닙니다."


def test_일반_질문은_넘지_않은_기준과_점포당_매출을_근거로_든다():
    text = answer_lead(_facts(), QuestionTopic("general"))
    assert "- [확인된 사실] 넘지 않은 경고 기준(송정동 한식): 포화." in text
    assert "점포당 월 평균 매출(송정동 한식, 2025년 4분기, 점포 13곳 평균): 약 433만 원" in text


def test_예산_질문은_예산으로_시작하고_충분한지는_판단할_수_없다고_쓴다():
    text = answer_lead(_facts(budget=50_000_000), QuestionTopic("budget"))
    lead = text.split("\n")[0]
    assert lead.startswith("[확인된 사실] 예산 5,000만 원으로 보면 송정동 한식은 권하지 않습니다")
    assert lead.endswith("예산이 충분한지는 이 리포트로 판단할 수 없습니다.")
    assert "상가 임대료(서울 기타 권역, 2026Q2): ㎡당 월 약 4.9만 원" in text
    assert f"- {BUDGET_GAP}" in text


def test_대출_질문은_전국_공시_금리와_상환_안내를_쓴다():
    text = answer_lead(_facts(), QuestionTopic("loan"))
    assert text.startswith("[확인된 사실] 대출을 끼고 시작한다면 송정동 한식은")
    assert "대출 금리(한국은행 ECOS 전국 공시 평균, 2026년 8월): 연 4.05% — 예상치이며 실제 심사 금리와 다릅니다." in text
    assert f"- {LOAN_NOTE}" in text


def test_프리필이_없으면_그_줄은_자료_부족이다():
    text = answer_lead(_facts(finance={"available": False, "reason": "프리필 조회 실패"}), QuestionTopic("budget"))
    assert "점포당 월 평균 매출(송정동 한식): 자료 부족 — 프리필 조회 실패" in text


def test_금액은_억과_만_원으로_쓴다():
    assert [won(50_000_000), won(100_000_000), won(150_000_000)] == ["5,000만 원", "1억 원", "1억 5,000만 원"]
```

- [ ] **Step 3: 실패 확인** — `.venv/bin/python -m pytest tests/test_question_answer.py -q` → ModuleNotFoundError.

- [ ] **Step 4: 구현** — `backend/apps/agent/domain/services/question_answer.py`

```python
"""질문에 대한 직접 답(첫 문장)과 근거 줄 — facts만으로 쓰는 순수 모듈 (stdlib만).

설계서 docs/superpowers/specs/2026-10-05-question-answer-design.md §5. 결론은 틀리면 안 되므로 코드가 쓰고,
LLM은 그 아래 해석만 쓴다. report_sections의 원칙(숫자에 범위·자료 부족은 이유와 함께·태그는 코드)을 따른다.
유형마다 Strategy 하나 — 첫 문장의 머리말·꼬리와 근거 줄만 다르다.
"""

import logging
from abc import ABC, abstractmethod

from apps.agent.domain.services.question_topic import QuestionTopic
from apps.agent.domain.services.report_sections import (
    FACT,
    SIGNAL_LABELS,
    missing,
    missing_reason,
    quarter_label,
    subject_names,
    topic_particle,
)

LOGGER = logging.getLogger(__name__)

BUDGET_GAP = (
    f"{FACT} 보증금·권리금·인테리어 비용 자료가 없어 예산이 충분한지는 판단할 수 없습니다 — "
    "자금 계획 화면에서 계산하세요."
)
LOAN_NOTE = (
    f"{FACT} 대출 원리금은 매출과 관계없이 매달 나갑니다 — 자금 계획 화면에서 상환액을 넣어 손익분기를 확인하세요."
)
_BUDGET_TAIL = " 예산이 충분한지는 이 리포트로 판단할 수 없습니다."
BAND_NAMES = {
    "lunch": "점심(11~14시)",
    "evening": "저녁(17~21시)",
    "night": "밤(21~06시)",
    "morning": "아침(06~11시)",
    "weekend": "주말",
}


def won(amount: int) -> str:
    """원 → '1억 5,000만 원'(만 원 아래는 버린다)."""
    eok, man = divmod(amount // 10_000, 10_000)
    parts = [*([f"{eok}억"] if eok else []), *([f"{man:,}만"] if man else [])]
    return " ".join(parts or ["0"]) + " 원"


def _object_particle(word: str) -> str:
    """목적 조사 — 받침이 있으면 '을', 없으면 '를'."""
    return "을" if (ord(word[-1]) - 0xAC00) % 28 else "를"


def _on_signals(verdict: dict) -> list[str]:
    """판정에 쓰인(참고 신호 아님) 켜진 신호 이름 — 꺼짐·계산 못 함은 뺀다."""
    return [
        SIGNAL_LABELS.get(s.get("key"), s.get("key"))
        for s in verdict.get("signals") or []
        if not s.get("advisory") and s.get("level") not in ("off", "unavailable")
    ]


# 판정 등급 → 결론 문장 (자료 부족·판정 대상 아님은 여기 오지 않는다 — scarce_lead 경로)
_LEADS = {
    "red": lambda subject, on: f"{subject} 권하지 않습니다 — 켜진 경고 신호 {len(on)}개({', '.join(on)}).",
    "orange": lambda subject, on: f"{subject} 조건부입니다 — {', '.join(on)}{_object_particle(on[-1])} 먼저 확인해야 합니다.",
    "clear": lambda subject, on: f"{subject} 경고 신호가 없습니다 — 다만 이것이 장사가 된다는 근거는 아닙니다.",
}


def _finance_item(facts: dict, key: str) -> tuple[dict | None, str | None]:
    """프리필 값 하나 → (항목, None) 또는 (None, 자료 부족 이유)."""
    finance = facts.get("finance") or {}
    reason = missing_reason(finance)
    if reason is not None:
        return None, reason
    item = finance.get(key) or {}
    if item.get("value") is None:
        return None, item.get("caveat") or "값 없음"
    return item, None


def revenue_line(facts: dict) -> str:
    region, industry = subject_names(facts)
    item, reason = _finance_item(facts, "expected_monthly_revenue")
    if item is None:
        return f"{FACT} 점포당 월 평균 매출({region} {industry}): {missing(reason)}"
    basis = item.get("basis") or {}
    return (
        f"{FACT} 점포당 월 평균 매출({region} {industry}, {quarter_label(basis.get('year_quarter'))}, "
        f"점포 {basis.get('store_count')}곳 평균): 약 {round(item['value'] / 10_000):,}만 원 — "
        "신규 점포는 평균 아래서 시작하는 경우가 많습니다."
    )


def rent_line(facts: dict) -> str:
    region, _ = subject_names(facts)
    item, reason = _finance_item(facts, "rent_per_m2")
    if item is None:
        return f"{FACT} 상가 임대료({region}): {missing(reason)}"
    basis = item.get("basis") or {}
    path = str(basis.get("region_path") or "").replace(">", " ")
    # 값 단위는 천원/㎡/월 — 만 원으로 쓴다
    return f"{FACT} 상가 임대료({path} 권역, {basis.get('period')}): ㎡당 월 약 {item['value'] / 10:.1f}만 원 — {item.get('caveat')}"


def loan_rate_line(facts: dict) -> str:
    item, reason = _finance_item(facts, "loan_rate")
    if item is None:
        return f"{FACT} 대출 금리(전국 공시 평균): {missing(reason)}"
    period = str((item.get("basis") or {}).get("period") or "")
    return (
        f"{FACT} 대출 금리(한국은행 ECOS 전국 공시 평균, {period[:4]}년 {int(period[4:])}월): "
        f"연 {item['value'] * 100:.2f}% — 예상치이며 실제 심사 금리와 다릅니다."
    )


class TopicAnswer(ABC):
    """한 유형의 직접 답 — 결론 문장은 판정 등급이 정하고, 유형은 머리말·꼬리·근거 줄만 정한다."""

    def head(self, facts: dict, topic: QuestionTopic) -> str:
        return ""

    def tail(self) -> str:
        return ""

    def lead(self, facts: dict, topic: QuestionTopic) -> str:
        region, industry = subject_names(facts)
        verdict = facts.get("verdict") or {}
        subject = f"{self.head(facts, topic)}{region} {industry}{topic_particle(industry)}"
        return f"{FACT} {_LEADS[verdict.get('verdict_code')](subject, _on_signals(verdict))}{self.tail()}"

    @abstractmethod
    def evidence(self, facts: dict, topic: QuestionTopic) -> list[str]:
        """근거 줄(태그 포함, 목록 기호 없음)."""


class GeneralAnswer(TopicAnswer):
    def evidence(self, facts: dict, topic: QuestionTopic) -> list[str]:
        region, industry = subject_names(facts)
        off = [
            SIGNAL_LABELS.get(s.get("key"), s.get("key"))
            for s in (facts.get("verdict") or {}).get("signals") or []
            if not s.get("advisory") and s.get("level") == "off"
        ]
        lines = [f"{FACT} 넘지 않은 경고 기준({region} {industry}): {', '.join(off)}."] if off else []
        return [*lines, revenue_line(facts)]


class BudgetAnswer(TopicAnswer):
    def head(self, facts: dict, topic: QuestionTopic) -> str:
        budget = facts.get("budget")
        return f"예산 {won(budget)}으로 보면 " if budget else ""

    def tail(self) -> str:
        return _BUDGET_TAIL

    def evidence(self, facts: dict, topic: QuestionTopic) -> list[str]:
        region, industry = subject_names(facts)
        budget = facts.get("budget")
        lines = [f"{FACT} 입력 예산({region} {industry} 창업): {won(budget)}."] if budget else []
        return [*lines, revenue_line(facts), rent_line(facts), BUDGET_GAP]


class LoanAnswer(TopicAnswer):
    def head(self, facts: dict, topic: QuestionTopic) -> str:
        return "대출을 끼고 시작한다면 "

    def evidence(self, facts: dict, topic: QuestionTopic) -> list[str]:
        return [loan_rate_line(facts), LOAN_NOTE]


# 유형 → Strategy (Task 4가 시간대·경쟁·대상 고객·코로나를 더한다)
_ANSWERS: dict[str, TopicAnswer] = {
    "general": GeneralAnswer(),
    "budget": BudgetAnswer(),
    "loan": LoanAnswer(),
}


def answer_lead(facts: dict, topic: QuestionTopic) -> str:
    """직접 답 마크다운 — 첫 문장, 빈 줄, 근거 줄 목록. 근거 작성이 예외를 내면 근거 자리만 자료 부족 한 줄."""
    strategy = _ANSWERS[topic.kind]
    try:
        lines = strategy.evidence(facts, topic)
    except Exception:
        LOGGER.exception("직접 답 근거 작성 실패 — %s", topic.kind)
        lines = [f"{FACT} {missing('일부 값이 비어 근거를 쓰지 못함')}"]
    return "\n\n".join([strategy.lead(facts, topic), "\n".join(f"- {line}" for line in lines)])
```

- [ ] **Step 5: 통과 확인** — `.venv/bin/python -m pytest tests/test_question_answer.py tests/test_report_sections.py -q` → 전부 통과. 기대 문자열이 실제와 다르면 **테스트가 아니라 구현을 설계서 §5에 맞춰** 고친다(단, e001 facts의 실제 값 때문에 생긴 차이면 보고하고 테스트 기대값을 실제 facts에 맞춘다).
- [ ] **Step 6: 커밋** — `git add -A backend/apps/agent/domain/services backend/tests/test_question_answer.py && git commit -m "backend: 질문 직접 답 첫 문장과 일반·예산·대출 근거"`

---

### Task 3: 본문 "그래도 한다면"에 거주민 줄·뉴스 줄

**Files:**
- Modify: `backend/apps/agent/domain/services/report_sections.py` (`_conditions` + 공개 함수 2개)
- Test: `backend/tests/test_report_sections.py` (테스트 3개 추가)

**Interfaces:**
- Consumes: Task 2의 공개 이름(`subject_names`, `missing_reason`).
- Produces: `resident_line(facts: dict) -> str`, `news_line(facts: dict) -> str | None` — Task 4 `CustomersAnswer`가 `resident_line`을 쓴다.
- facts 모양: `population = {"period": "202606", "age_distribution": {"0": 348, "5": 490, ..., "100": 8}}`(5세 구간 키), `profile.apartment_avg_price_won`(원), `news = [{"content": "제목\n본문", "url": ..., "published_at": "2026-09-11T08:55:00"}, ...]`.

- [ ] **Step 1: 실패하는 테스트** (`tests/test_report_sections.py` 끝에 추가 — 파일 상단의 `_BASE`(e001 송정동) 재사용, import에 `news_line, resident_line` 추가)

```python
def test_그래도_한다면에_주민_연령과_아파트_시가를_쓴다():
    facts = {
        **_BASE,
        "population": {"period": "202606", "age_distribution": {"10": 20, "20": 30, "35": 10, "60": 25, "85": 15}},
        "profile": {**_BASE["profile"], "apartment_avg_price_won": 480_839_259},
    }
    assert resident_line(facts) == (
        "[확인된 사실] 주민(송정동, 2026년 6월 주민등록): 60세 이상 40%, 20~39세 40%"
        " · 아파트 평균 시가 약 4.8억 원(동별 편차가 커 참고값입니다)."
    )
    assert resident_line(facts) in build_sections(facts)["conditions"]


def test_뉴스_줄은_동_이름이_든_기사만_최신순으로_싣는다():
    news = [
        {"content": "송파구 쿠킹 클래스\n본문", "url": "u1", "published_at": "2026-09-30T00:00:00"},
        {"content": "송정동 골목 상점가 지정\n송정동 본문", "url": "u2", "published_at": "2026-09-01T00:00:00"},
        {"content": "﻿송정 시장 새단장\n본문", "url": "u3", "published_at": "2026-09-20T00:00:00"},
    ]
    assert news_line({**_BASE, "news": news}) == (
        "[참고 신호] 송정동 이름이 나온 최근 뉴스: 송정 시장 새단장(2026-09-20) · 송정동 골목 상점가 지정(2026-09-01)"
    )


def test_동_이름이_든_기사가_없으면_뉴스_줄을_뺀다():
    facts = {**_BASE, "news": [{"content": "송파구 기사", "url": "u1", "published_at": "2026-09-30T00:00:00"}]}
    assert news_line(facts) is None
    assert "최근 뉴스" not in build_sections(facts)["conditions"]
```

- [ ] **Step 2: 실패 확인** — `.venv/bin/python -m pytest tests/test_report_sections.py -q` → ImportError.

- [ ] **Step 3: 구현** — `report_sections.py`에 `import re` 추가, `_conditions` 위(“그래도 한다면” 구역)에 아래 함수를 넣고 `_conditions`의 lines에 `resident_line(facts)`와 뉴스 줄을 더한다.

```python
# 동 이름 꼬리(번호·"제"·"가"·"동") — 남은 어간이 기사에 나오면 이 동 기사로 본다(상도제1동→상도, 종로1.2.3.4가동→종로)
_DONG_SUFFIX = re.compile(r"(?:제?\d+(?:\.\d+)*가?동|동)$")
_NEWS_MAX = 3


def resident_line(facts: dict) -> str:
    """주민 연령 구성(주민등록)과 아파트 평균 시가(참고값) — 사람 검수 "거주민 생활수준" 메모(설계서 §6)."""
    region, _ = subject_names(facts)
    population = facts.get("population") or {}
    ages = population.get("age_distribution") or {}
    total = sum(ages.values())
    reason = missing_reason(population)
    if reason is not None or not total:
        head = f"{FACT} 주민({region}): {missing(reason or '연령별 인구 없음')}"
    else:
        old = sum(v for k, v in ages.items() if int(k) >= 60) / total
        young = sum(v for k, v in ages.items() if 20 <= int(k) < 40) / total
        period = str(population.get("period") or "")
        head = (
            f"{FACT} 주민({region}, {period[:4]}년 {int(period[4:])}월 주민등록): "
            f"60세 이상 {old * 100:.0f}%, 20~39세 {young * 100:.0f}%"
        )
    price = (facts.get("profile") or {}).get("apartment_avg_price_won")
    tail = f" · 아파트 평균 시가 약 {price / 100_000_000:.1f}억 원(동별 편차가 커 참고값입니다)" if price else ""
    return f"{head}{tail}."


def news_line(facts: dict) -> str | None:
    """동 이름이 든 기사만 최신순 최대 3건 — 뉴스 검색은 다른 구 기사가 섞여 와서 거른다. 없으면 None(줄 생략)."""
    region, _ = subject_names(facts)
    base = _DONG_SUFFIX.sub("", region)
    news = facts.get("news")
    if len(base) < 2 or not isinstance(news, list):
        return None
    hits = sorted(
        (h for h in news if base in (h.get("content") or "")),
        key=lambda h: h.get("published_at") or "",
        reverse=True,
    )
    unique: dict[str, dict] = {}
    for hit in hits:
        unique.setdefault(hit.get("url") or hit.get("content"), hit)
    items = [
        f"{(h.get('content') or '').split(chr(10))[0].lstrip(chr(0xFEFF)).strip()}({(h.get('published_at') or '')[:10]})"
        for h in list(unique.values())[:_NEWS_MAX]
    ]
    return f"{SIGNAL} {region} 이름이 나온 최근 뉴스: " + " · ".join(items) if items else None
```

`_conditions` 교체본:

```python
def _conditions(facts: dict) -> str:
    region, industry = subject_names(facts)
    news = news_line(facts)
    lines = [
        _hours(facts.get("hour_gap") or {}, region, industry),
        _profile(facts.get("profile") or {}, region),
        _staying(facts.get("commerce_change") or {}, region),
        resident_line(facts),
        *([news] if news else []),
        *([_BUDGET_LINE] if facts.get("budget") is not None else []),
    ]
    return "\n\n".join(lines)
```

- [ ] **Step 4: 통과 확인** — `.venv/bin/python -m pytest tests/test_report_sections.py tests/test_agent_loop.py -q` → 통과. 이어서 범위 검사 회귀 확인: `cd .. && backend/.venv/bin/python -m apps.agent.adapter.inbound.cli.benchmark_report sections-check --scenario-set 150` 를 `backend`에서 실행(`cd backend && .venv/bin/python -m apps.agent.adapter.inbound.cli.benchmark_report sections-check --scenario-set 150`) → "150건 중 문제 0건". 문제가 나오면 해당 줄에 범위 낱말(동 이름 등)이 빠진 것이니 문장을 고친다. 이 명령은 `data/eval/cache/llm-benchmark/report/sections_check.json`을 덮어쓴다 — 캐시 심링크라 본진에도 반영되며, 그 파일은 재생성 가능한 산출물이라 괜찮다.
- [ ] **Step 5: 커밋** — `git commit -am "backend: 그래도 한다면 절에 주민 연령·아파트 시가 줄과 동 이름 뉴스 줄"`

---

### Task 4: 시간대·주말·경쟁·대상 고객·코로나 근거

**Files:**
- Modify: `backend/apps/agent/domain/services/question_answer.py`
- Test: `backend/tests/test_question_answer.py` (테스트 추가)

**Interfaces:**
- Consumes: Task 2 `TopicAnswer`·`_ANSWERS`·`BAND_NAMES`, Task 3 `resident_line`, report_sections `HOUR_BAND_LABELS`·`DISASTER_NOTE`·`current_year`.
- Produces: `_ANSWERS`에 `hours`·`competition`·`customers`·`covid` 키 — 이후 모든 `classify` 결과가 `answer_lead`로 처리된다.
- facts 모양: `hour_gap = {"available": True, "year_quarter": "20254", "bands": [{"hour_band": "11_14", "footfall_intensity": 0.99, "sales_intensity": 0.35, "gap": ...}, ...]}`(강도 1.0 = 24시간 균등의 시간당 값), `profile.weekend_index`(주말 하루 유동 ÷ 평일 하루), `profile.benchmarks.type_median.weekend_index`, `profile.benchmarks.type_count`, `profile.type_name`, `profile.footfall_age_mix = [{"age": "20", "share": 0.22}, ...]`(age: 10·20·30·40·50·60_over), `profile.worker_resident_ratio`, `metrics_history = [{"year": 2019, "store_count": 41, "closure_rate": 0.0278}, ...]`. e001: hour_gap 없음, weekend 0.986·중앙값 1.041·주거형·251개, 연령 상위 20대 22%·30대 20%, 직장/상주 0.077, 2026년은 진행 중(분기 20262).

- [ ] **Step 1: 실패하는 테스트** (`test_question_answer.py`에 추가)

```python
_BANDS = {
    "available": True,
    "year_quarter": "20254",
    "bands": [
        {"hour_band": "11_14", "footfall_intensity": 0.989, "sales_intensity": 0.346},
        {"hour_band": "21_24", "footfall_intensity": 1.005, "sales_intensity": 2.377},
        {"hour_band": "00_06", "footfall_intensity": 1.029, "sales_intensity": 0.281},
    ],
}


def test_점심_질문은_그_구간의_사람_흐름과_매출_강도를_쓴다():
    text = answer_lead(_facts(hour_gap=_BANDS), QuestionTopic("hours", "lunch"))
    assert text.startswith("[확인된 사실] 점심(11~14시) 위주로 보면 송정동 한식은")
    assert "점심(11~14시)(송정동 유동인구·한식 매출, 2025년 4분기): 사람 흐름은 시간당 하루 평균의 0.99배, 매출은 0.35배." in text


def test_밤_질문은_밤과_새벽_두_구간을_쓴다():
    text = answer_lead(_facts(hour_gap=_BANDS), QuestionTopic("hours", "night"))
    assert "밤(21~24시)(송정동" in text and "새벽(00~06시)(송정동" in text


def test_시간대_자료가_없으면_자료_부족과_동_사람_흐름을_쓴다():
    text = answer_lead(_facts(), QuestionTopic("hours", "evening"))  # e001은 hour_gap 없음
    assert "시간대(송정동 한식): 자료 부족 — 시간대 어긋남 자료가 없다" in text
    assert "사람 흐름(송정동 동 전체, 2026년 2분기): 가장 많은 때" in text


def test_주말_질문은_주말_평일_비를_같은_유형_중앙값과_비교한다():
    text = answer_lead(_facts(), QuestionTopic("hours", "weekend"))
    assert "주말(송정동 동 전체, 2026년 2분기): 주말 하루 유동인구는 평일 하루의 0.99배 — 같은 유형(주거형) 251개 동 중앙값 1.04배." in text


def test_경쟁_질문은_포화_근거와_점포_수_추이와_순유출을_쓴다():
    text = answer_lead(_facts(), QuestionTopic("competition"))
    assert "- [확인된 사실] 포화(송정동 한식): " in text
    assert "송정동 한식 점포 수: 2024년 42곳 → 2025년 42곳 → 2026년(올해 현재까지) 33곳." in text
    assert "- [확인된 사실] 순유출(송정동 한식): " in text


def test_외국인_질문은_주민_연령과_외국인_자료_없음을_쓴다():
    text = answer_lead(_facts(), QuestionTopic("customers", "foreign"))
    assert "주민(송정동, " in text
    assert "유동인구 연령 상위(송정동 동 전체, 2026년 2분기): 20대 22%, 30대 20%." in text
    assert "직장인구 ÷ 상주인구(송정동, 2026년 2분기): 0.08배." in text
    assert "- [확인된 사실] 외국인 주민·방문객 자료는 없습니다." in text
    assert "외국인" not in answer_lead(_facts(), QuestionTopic("customers"))


def test_코로나_질문은_코로나_전후_폐업률과_최근_완결_연도를_쓴다():
    text = answer_lead(_facts(), QuestionTopic("covid"))
    assert "송정동 한식 연간 폐업률(코로나 전후): 2019년 2.8% · 2020년 17.1% · 2021년 9.8% · 2022년 16.7% · 2023년 2.7%." in text
    assert "송정동 한식 최근 완결 연도(2025년) 폐업률: 19.0%." in text
```

- [ ] **Step 2: 실패 확인** — KeyError('hours') 등.

- [ ] **Step 3: 구현** — `question_answer.py`의 import에 `DISASTER_NOTE, HOUR_BAND_LABELS, current_year, resident_line`(report_sections) 추가, `_ANSWERS` 정의 **위**에 아래를 넣고 `_ANSWERS`에 4개 키를 더한다.

```python
# 묻는 구간 → 원천 6구간 (밤은 21~24시와 00~06시 두 구간)
_BAND_CODES = {"lunch": ("11_14",), "evening": ("17_21",), "night": ("21_24", "00_06"), "morning": ("06_11",)}
_AGE_NAMES = {"10": "10대", "20": "20대", "30": "30대", "40": "40대", "50": "50대", "60_over": "60대 이상"}
_FOREIGN_LINES = {"foreign": [f"{FACT} 외국인 주민·방문객 자료는 없습니다."]}  # 질문 전제를 사실로 받지 않는다(응답 규칙 ①)
_COVID_YEARS = range(2019, 2024)


def _flow_line(facts: dict) -> str:
    region, _ = subject_names(facts)
    profile = facts.get("profile") or {}
    reason = missing_reason(profile)
    if reason is not None:
        return f"{FACT} 사람 흐름({region}): {missing(reason)}"
    return (
        f"{FACT} 사람 흐름({region} 동 전체, {quarter_label(profile.get('year_quarter'))}): "
        f"가장 많은 때 {profile.get('peak_block_name')}, 가장 적은 때 {profile.get('trough_block_name')}."
    )


def _band_lines(facts: dict, topic: QuestionTopic) -> list[str]:
    region, industry = subject_names(facts)
    hour_gap = facts.get("hour_gap") or {}
    if not hour_gap.get("available"):
        reason = (hour_gap.get("reason") or "").split(":")[0].strip()  # 내부 코드(": 동코드 × 업종")는 숨긴다
        return [f"{FACT} 시간대({region} {industry}): {missing(reason)}", _flow_line(facts)]
    bands = {b["hour_band"]: b for b in hour_gap.get("bands") or []}
    when = quarter_label(hour_gap.get("year_quarter"))
    lines = [
        f"{FACT} {HOUR_BAND_LABELS[code]}({region} 유동인구·{industry} 매출, {when}): "
        f"사람 흐름은 시간당 하루 평균의 {bands[code]['footfall_intensity']:.2f}배, 매출은 {bands[code]['sales_intensity']:.2f}배."
        for code in _BAND_CODES[topic.detail]
        if code in bands
    ]
    return lines or [f"{FACT} 시간대({region} {industry}): {missing('묻는 구간 자료 없음')}"]


def _weekend_lines(facts: dict, topic: QuestionTopic) -> list[str]:
    region, _ = subject_names(facts)
    profile = facts.get("profile") or {}
    reason = missing_reason(profile)
    weekend = profile.get("weekend_index")
    if reason is not None or weekend is None:
        return [f"{FACT} 주말({region}): {missing(reason or '주말 유동인구 자료 없음')}"]
    benchmarks = profile.get("benchmarks") or {}
    median = (benchmarks.get("type_median") or {}).get("weekend_index")
    compare = (
        f" — 같은 유형({profile.get('type_name')}) {benchmarks.get('type_count')}개 동 중앙값 {median:.2f}배"
        if median is not None
        else ""
    )
    return [
        f"{FACT} 주말({region} 동 전체, {quarter_label(profile.get('year_quarter'))}): "
        f"주말 하루 유동인구는 평일 하루의 {weekend:.2f}배{compare}."
    ]


_HOURS_EVIDENCE = {"weekend": _weekend_lines}  # 나머지 구간은 _band_lines


class HoursAnswer(TopicAnswer):
    def head(self, facts: dict, topic: QuestionTopic) -> str:
        return f"{BAND_NAMES[topic.detail]} 위주로 보면 "

    def evidence(self, facts: dict, topic: QuestionTopic) -> list[str]:
        return _HOURS_EVIDENCE.get(topic.detail, _band_lines)(facts, topic)


def _signal_line(facts: dict, key: str) -> str:
    region, industry = subject_names(facts)
    signal = next((s for s in (facts.get("verdict") or {}).get("signals") or [] if s.get("key") == key), None)
    evidence = signal.get("evidence") if signal else missing("신호 없음")
    return f"{FACT} {SIGNAL_LABELS[key]}({region} {industry}): {evidence}"


def _store_trend(facts: dict) -> str:
    region, industry = subject_names(facts)
    history = facts.get("metrics_history")
    reason = missing_reason(history)
    rows = [r for r in history or [] if r.get("store_count") is not None][-3:] if reason is None else []
    if not rows:
        return f"{FACT} {region} {industry} 점포 수: {missing(reason or '연도별 점포 수 없음')}"
    year = current_year(facts)
    steps = " → ".join(
        f"{r['year']}년{'(올해 현재까지)' if str(r['year']) == year else ''} {r['store_count']}곳" for r in rows
    )
    return f"{FACT} {region} {industry} 점포 수: {steps}."


class CompetitionAnswer(TopicAnswer):
    def evidence(self, facts: dict, topic: QuestionTopic) -> list[str]:
        return [_signal_line(facts, "saturation"), _store_trend(facts), _signal_line(facts, "net_outflow")]


class CustomersAnswer(TopicAnswer):
    def evidence(self, facts: dict, topic: QuestionTopic) -> list[str]:
        region, _ = subject_names(facts)
        profile = facts.get("profile") or {}
        foreign = _FOREIGN_LINES.get(topic.detail, [])
        reason = missing_reason(profile)
        if reason is not None:
            return [resident_line(facts), f"{FACT} 유동인구({region}): {missing(reason)}", *foreign]
        when = quarter_label(profile.get("year_quarter"))
        mix = sorted(profile.get("footfall_age_mix") or [], key=lambda a: -a["share"])[:2]
        ages = ", ".join(f"{_AGE_NAMES.get(a['age'], a['age'])} {a['share'] * 100:.0f}%" for a in mix)
        return [
            resident_line(facts),
            f"{FACT} 유동인구 연령 상위({region} 동 전체, {when}): {ages}.",
            f"{FACT} 직장인구 ÷ 상주인구({region}, {when}): {profile['worker_resident_ratio']:.2f}배.",
            *foreign,
        ]


class CovidAnswer(TopicAnswer):
    def evidence(self, facts: dict, topic: QuestionTopic) -> list[str]:
        region, industry = subject_names(facts)
        history = facts.get("metrics_history")
        reason = missing_reason(history)
        rows = [r for r in history or [] if r.get("closure_rate") is not None] if reason is None else []
        window = [r for r in rows if r["year"] in _COVID_YEARS]
        if not window:
            return [f"{FACT} {region} {industry} 코로나 전후 폐업률: {missing(reason or '2019~2023년 폐업률 없음')}"]
        rates = " · ".join(f"{r['year']}년 {r['closure_rate'] * 100:.1f}%" for r in window)
        lines = [f"{FACT} {region} {industry} 연간 폐업률(코로나 전후): {rates}. {DISASTER_NOTE}"]
        year = current_year(facts)
        done = [r for r in rows if str(r["year"]) != year]
        if done:
            lines.append(f"{FACT} {region} {industry} 최근 완결 연도({done[-1]['year']}년) 폐업률: {done[-1]['closure_rate'] * 100:.1f}%.")
        return lines
```

`_ANSWERS`에 추가: `"hours": HoursAnswer(), "competition": CompetitionAnswer(), "customers": CustomersAnswer(), "covid": CovidAnswer()`.

- [ ] **Step 4: 통과 확인** — `.venv/bin/python -m pytest tests/test_question_answer.py -q`. 기대 문자열이 e001 실제 값과 어긋나면 실제 facts를 확인해 테스트 기대값을 맞추고 보고서에 적는다.
- [ ] **Step 5: 커밋** — `git commit -am "backend: 질문 직접 답 — 시간대·주말·경쟁·대상 고객·코로나 근거"`

---

### Task 5: facts에 자금 계획 프리필과 질문 속 예산

**Files:**
- Modify: `backend/apps/agent/app/ports/output/agent_port.py` (포트 2개)
- Create: `backend/apps/agent/adapter/outbound/gateways/finance_facts_gateway.py`, `backend/apps/agent/adapter/outbound/gateways/question_budget_gateway.py`
- Modify: `backend/apps/agent/app/use_cases/report_facts.py`, `backend/apps/agent/dependencies/analysis_dependencies.py`, `backend/apps/agent/adapter/inbound/cli/benchmark_report.py` (`_collector`만)
- Test: `backend/tests/test_agent_report_facts.py`

**Interfaces:**
- Produces: `FinanceFactsPort.prefill(region_code: str, industry_id: str) -> dict`, `QuestionBudgetPort.parse(question: str) -> int | None`; `ReportFactsCollector(..., finance_facts: FinanceFactsPort | None = None, question_budget: QuestionBudgetPort | None = None)`; `FACTS_KEYS` 끝에 `"finance"`(14키); `FinanceFactsGateway`, `QuestionBudgetGateway`.

- [ ] **Step 1: 실패하는 테스트** (`test_agent_report_facts.py` — 기존 `test_열세_키를_빠짐없이_모은다`를 아래 첫 테스트로 **교체**, 나머지 추가. import에 `FinanceFactsPort, QuestionBudgetPort` 추가)

```python
def test_열네_키를_빠짐없이_모은다():
    """프론트 시각 자료가 키 하나에 하나씩 달린다 — 키가 빠지면 그림이 사라진다 (설계서 §5)."""
    facts = _collector().collect("1168064000", "korean_food", 50_000_000)

    assert list(facts) == list(FACTS_KEYS)
    assert len(FACTS_KEYS) == 14 and FACTS_KEYS[-1] == "finance"


class FakeFinanceFacts(FinanceFactsPort):
    def __init__(self, failing: bool = False) -> None:
        self._failing = failing

    def prefill(self, region_code: str, industry_id: str) -> dict:
        if self._failing:
            raise RuntimeError("프리필 조회 실패")
        return {"available": True, "loan_rate": {"value": 0.0405, "unit": "비율", "basis": {"period": "202608"}, "caveat": "공시"}}


class FakeQuestionBudget(QuestionBudgetPort):
    def parse(self, question: str) -> int | None:
        return 50_000_000 if "5천만" in question else None


def _with_new_ports(finance=None) -> ReportFactsCollector:
    return ReportFactsCollector(
        region_facts=FakeRegionFacts(),
        verdict_facts=FakeVerdictFacts(),
        funding_facts=FakeFundingFacts(),
        news_search=FakeNewsSearch(),
        finance_facts=finance or FakeFinanceFacts(),
        question_budget=FakeQuestionBudget(),
    )


def test_자금_계획_프리필을_싣고_실패하면_그_자리만_비운다():
    assert _with_new_ports().collect("1168064000", "korean_food")["finance"]["loan_rate"]["value"] == 0.0405
    failed = _with_new_ports(FakeFinanceFacts(failing=True)).collect("1168064000", "korean_food")["finance"]
    assert failed["available"] is False and "프리필 조회 실패" in failed["reason"]


def test_폼_예산이_없으면_질문_속_금액을_예산으로_싣는다():
    collector = _with_new_ports()
    assert collector.collect("1168064000", "hair_salon", None, "모아 둔 돈이 5천만 원")["budget"] == 50_000_000
    assert collector.collect("1168064000", "hair_salon", 70_000_000, "모아 둔 돈이 5천만 원")["budget"] == 70_000_000
    assert collector.collect("1168064000", "hair_salon", None, None)["budget"] is None
```

- [ ] **Step 2: 실패 확인** — ImportError(FinanceFactsPort).

- [ ] **Step 3: 포트** (`agent_port.py` 끝에 추가)

```python
class FinanceFactsPort(ABC):
    """Driven Port — finance BC의 자금 계획 프리필(동·업종 점포당 월 평균 매출·권역 임대료·공시 금리).

    질문 직접 답의 예산·대출 근거로 쓴다 (설계서 2026-10-05-question-answer §7).
    """

    @abstractmethod
    def prefill(self, region_code: str, industry_id: str) -> dict:
        """{"available": True, "expected_monthly_revenue"|"rent_per_m2"|"loan_rate": {value, unit, basis, caveat}}."""


class QuestionBudgetPort(ABC):
    """Driven Port — 질문 속 금액(원). 의도 관문과 같은 규칙을 쓴다."""

    @abstractmethod
    def parse(self, question: str) -> int | None:
        """금액이 없으면 None."""
```

- [ ] **Step 4: 게이트웨이 2개**

`finance_facts_gateway.py`:
```python
"""Driven Adapter — finance BC 프리필 호출 (cross-BC 접근은 이 파일 안에서만)."""

from dataclasses import asdict

from apps.agent.app.ports.output.agent_port import FinanceFactsPort
from apps.finance.dependencies.finance_dependencies import get_finance_use_case

_KEYS = ("expected_monthly_revenue", "rent_per_m2", "loan_rate")  # 비용 비율은 직접 답에 쓰지 않는다


class FinanceFactsGateway(FinanceFactsPort):
    def prefill(self, region_code: str, industry_id: str) -> dict:
        prefill = get_finance_use_case().prefill(region_code, industry_id)
        return {"available": True, **{key: asdict(getattr(prefill, key)) for key in _KEYS}}
```

`question_budget_gateway.py`:
```python
"""Driven Adapter — 의도 관문의 금액 규칙 재사용 (cross-BC 접근은 이 파일 안에서만)."""

from apps.agent.app.ports.output.agent_port import QuestionBudgetPort
from apps.intent.domain.services.extractors import parse_budget


class QuestionBudgetGateway(QuestionBudgetPort):
    def parse(self, question: str) -> int | None:
        return parse_budget(question)
```

- [ ] **Step 5: 수집기** (`report_facts.py`)
  - import에 `FinanceFactsPort, QuestionBudgetPort` 추가, `FACTS_KEYS` 끝에 `"finance",` 추가, 모듈 docstring의 "13항목" → "14항목".
  - `__init__`에 `finance_facts: FinanceFactsPort | None = None, question_budget: QuestionBudgetPort | None = None` 인자와 필드.
  - `futures`에 `"finance": pool.submit(self._finance, region, industry),` (`"funding_candidates"` 다음, `"news"` 앞).
  - `values["budget"] = budget` → `values["budget"] = budget if budget is not None else self._question_budget_of(question)`.
  - docstring "§5 계약 표의 13키" → "14키".
  - 메서드:

```python
    def _finance(self, region: str, industry: str) -> dict:
        if self._finance_facts is None:
            return {"available": False, "reason": "자금 계획 프리필이 연결되지 않았습니다"}
        return self._finance_facts.prefill(region, industry)

    def _question_budget_of(self, question: str | None) -> int | None:
        """폼 예산이 없을 때만 — 질문 속 금액(관문과 같은 규칙)."""
        if not question or self._question_budget is None:
            return None
        return self._question_budget.parse(question)
```

- [ ] **Step 6: 배선** — `analysis_dependencies.py`의 `ReportFactsCollector(...)`와 `benchmark_report.py`의 `_collector()` 양쪽에 `finance_facts=FinanceFactsGateway(), question_budget=QuestionBudgetGateway(),` 추가(+ import).

- [ ] **Step 7: 통과 확인** — `.venv/bin/python -m pytest -q` 전체 → 통과. 실DB 확인(읽기 전용): `.venv/bin/python -c "from apps.agent.adapter.outbound.gateways.finance_facts_gateway import FinanceFactsGateway as G; print(G().prefill('1150060500','hair_salon')['rent_per_m2'])"` → value·basis가 나온다.
- [ ] **Step 8: 커밋** — `git add -A backend && git commit -m "backend: facts에 자금 계획 프리필(finance)·질문 속 예산"`

---

### Task 6: 해석 흐름 — answer_lead 절과 LLM 입력·지시

**Files:**
- Modify: `backend/apps/agent/app/use_cases/analysis_interactor.py`, `backend/apps/agent/domain/services/section_stream.py`
- Test: `backend/tests/test_agent_loop.py`, `backend/tests/test_agent_section_stream.py`(순서 테스트가 있으면 기대값 갱신)

**Interfaces:**
- Consumes: `classify`, `answer_lead`, `scarcity`.
- Produces: SSE `report_delta {section: "answer_lead"}` (질문 있음·자료 부족 아님일 때만, 6개 절보다 **먼저**); 상수 `QUESTION_SYSTEM_PROMPT`, `LEAD_FALLBACK = "해석을 만들지 못했습니다. 위 답과 아래 사실을 직접 확인해 주세요."`; `TOPIC_NAMES: dict[str, str]`; `answer_message(facts, question, sections, lead: str | None = None)`; `SECTION_ORDER = ("answer_lead", "answer", "verdict", ...)`.

- [ ] **Step 1: 실패하는 테스트** (`test_agent_loop.py`에 추가 — e001은 red, 대안에 경고 없음 있음. import에 `LEAD_FALLBACK, QUESTION_SYSTEM_PROMPT` 추가)

```python
def test_질문이_있으면_직접_답을_여섯_절보다_먼저_낸다():
    _, events = _run(FakeLLM([_ANSWER]), question="은행 대출 받아서 차려도 될까요?")

    sections = [e.payload["section"] for e in events if e.type == "report_delta"]
    assert sections == ["answer_lead", *SECTION_TITLES, "answer"]
    assert _deltas(events)["answer_lead"].startswith("[확인된 사실] 대출을 끼고 시작한다면 송정동 한식은 권하지 않습니다")


def test_질문이_있으면_LLM에_유형과_직접_답을_주고_해석만_시킨다():
    llm = FakeLLM([_ANSWER])
    _run(llm, question="주말 손님 위주로 생각하고 있는데 어떨까요?")

    messages = llm.calls[0][0]
    assert messages[0]["content"] == QUESTION_SYSTEM_PROMPT
    user = messages[1]["content"]
    assert "질문 유형: 시간대" in user
    assert user.index("[이미 화면에 나간 직접 답과 근거]") < user.index("[리포트 본문]")


def test_질문이_있을_때_해석이_실패하면_위_답을_가리키는_문장으로_맺는다():
    _, events = _run(FakeLLM([RuntimeError("down")]), question="여기서 한식당 차려도 괜찮을까요?")
    assert _deltas(events)["answer"].startswith(LEAD_FALLBACK)


def test_질문이_없으면_직접_답_절이_없다():
    _, events = _run(FakeLLM([_ANSWER]))
    assert "answer_lead" not in _deltas(events)
```

또 `test_자료_부족_동네는_LLM을_부르지_않고_코드_첫_문장만_낸다`에 질문을 준 경우에도 `answer_lead`가 없음을 단언 한 줄 추가(그 테스트가 쓰는 facts·호출 모양을 따른다).

- [ ] **Step 2: 실패 확인** — `.venv/bin/python -m pytest tests/test_agent_loop.py -q`.

- [ ] **Step 3: 구현** (`analysis_interactor.py`)
  - import: `from apps.agent.domain.services.question_answer import answer_lead`, `from apps.agent.domain.services.question_topic import QuestionTopic, classify`.
  - 프롬프트를 공통 규칙 + 두 머리로 나눈다(기존 `SYSTEM_PROMPT` 문자열 결과는 뉴스 규칙 한 줄만 늘어난다):

```python
_COMMON_RULES = """
- 제목·목록·표·굵은 글씨를 쓰지 않는다.
- 숫자를 쓰지 않는다 — 아라비아 숫자는 한 글자도 쓰지 않는다. 숫자는 본문이 범위와 함께 보여 준다.
  링크·공고 번호도 쓰지 않는다.
- 판정 등급을 바꾸거나 새로 매기지 않는다. 본문에 없는 사실을 보태지 않는다.
- 본문이 "자료 부족"이라고 한 곳은 추정으로 메우지 않고 "자료가 부족해 판단할 수 없다"고 말한다.
- 뉴스는 [참고 신호]라고 밝히고만 쓴다. 뉴스로 판정이나 결론을 바꾸지 않는다.

[응답 규칙]
① 외국인 관련 내용은 업종 타깃 정합성 문맥으로만 쓴다. 비하·차별 표현은 금지한다.
② 코로나 재난지원 시기(재난지원금·손실보상으로 폐업이 늦춰졌을 수 있는 해)의 폐업률은 왜곡됐을 수 있음을 감안한다.
③ 대출 중개와 특정 은행·상품 추천은 금지한다. 금리·한도를 말하면 "예상치"라고 밝힌다."""

SYSTEM_PROMPT = """당신은 서울 창업 경고 리포트 맨 위의 "해석" 한 단락을 쓴다.
사용자 메시지에 총평 요청과, 화면에 이미 나간 리포트 본문 6개 절이 주어진다.
본문은 코드가 사실에서 쓴 글이다 — 본문만 근거로 삼는다.

[출력 규칙]
- 3~5문장, 한 단락. 이 동네에서 이 업종을 한다면 먼저 볼 것을 총평한다.""" + _COMMON_RULES

QUESTION_SYSTEM_PROMPT = """당신은 서울 창업 경고 리포트 맨 위 "질문에 대한 답" 상자의 해석 단락을 쓴다.
사용자 메시지에 질문, 질문 유형, 화면에 이미 나간 직접 답(첫 문장)과 근거, 리포트 본문 6개 절이 주어진다.
직접 답·근거·본문은 코드가 사실에서 쓴 글이다 — 이것만 근거로 삼는다.

[출력 규칙]
- 2~3문장, 한 단락. 직접 답이 왜 그런지 본문을 근거로 해석한다. 직접 답을 되풀이하지 않는다.
- 직접 답의 결론을 뒤집거나 흐리지 않는다(예: "권하지 않는다"를 "해볼 만하다"로).""" + _COMMON_RULES
```

  - 기존 `test_시스템_프롬프트가_숫자와_등급_변경과_추정을_금지한다`·`test_응답_규칙_2는…`이 문구를 단언하면 그 단언이 여전히 맞는지 확인(문구는 그대로 옮겼다). "질문이 있으면 첫 문장에서 질문에 직접 답한다" 문구를 단언하는 테스트가 있으면 새 구조에 맞게 고친다.
  - 상수:

```python
LEAD_FALLBACK = "해석을 만들지 못했습니다. 위 답과 아래 사실을 직접 확인해 주세요."
TOPIC_NAMES = {
    "loan": "대출",
    "budget": "예산",
    "hours": "시간대",
    "competition": "경쟁",
    "customers": "대상 고객",
    "covid": "코로나",
    "general": "일반(이 자리 괜찮은가)",
}
```

  - `answer_message`에 `topic: QuestionTopic | None = None, lead: str | None = None` 인자: lead가 있으면 `[f"분석 지역: …", f"사용자 질문: {question}", f"질문 유형: {TOPIC_NAMES[topic.kind]}", "[이미 화면에 나간 직접 답과 근거]", lead, "[리포트 본문]", 본문]`, 없으면 기존과 같다.
  - `run`: `sections = build_sections(facts)` 다음에

```python
        topic = classify(question)
        lead = answer_lead(facts, topic) if topic is not None and scarcity(facts) is None else None
        if lead is not None:  # 직접 답은 코드라 사실이 모이자마자 맨 먼저 나간다
            yield AgentEvent("report_delta", {"section": "answer_lead", "markdown": lead})
        for name, markdown in sections.items():
            ...
        answer = self._answer(facts, question, sections, topic, lead)
```

  - `_answer(self, facts, question, sections, topic, lead)`: scarcity 분기는 그대로. 메시지는 `{"role": "system", "content": QUESTION_SYSTEM_PROMPT if lead else SYSTEM_PROMPT}`, `answer_message(facts, question, sections, topic, lead)`. 폴백은 `fallback = LEAD_FALLBACK if lead else ANSWER_FALLBACK` 후 기존처럼 pointer를 붙인다. (`lead` 유무 두 갈래뿐인 선택이라 삼항으로 둔다.)
  - 모듈 docstring 순서 설명에 "질문이 있으면 코드 직접 답(`answer_lead`)이 6개 절보다 먼저" 한 줄 추가.

- [ ] **Step 4: section_stream** — `SECTION_ORDER = ("answer_lead", "answer", "verdict", "reasons", "analogs", "conditions", "alternatives", "funding")`, 주석에 "질문에 대한 직접 답(answer_lead, 코드)이 맨 위, 그 아래 해석" 반영. `tests/test_agent_section_stream.py`가 순서를 단언하면 기대값 갱신.

- [ ] **Step 5: 통과 확인** — `.venv/bin/python -m pytest -q` 전체 통과.
- [ ] **Step 6: 커밋** — `git commit -am "backend: 질문 직접 답 절(answer_lead) 즉시 송출·해석 입력과 지시 변경"`

---

### Task 7: 벤치 — facts 보강·sections-check·판정 묶음·기준표 v2·버전 로그

**Files:**
- Modify: `backend/apps/agent/adapter/inbound/cli/benchmark_report.py`, `backend/apps/agent/adapter/inbound/cli/report_bench_scoring.py`, `data/eval/report_answer_rubric.md`, `backend/docs/backend_ver_log.md`
- Test: `backend/tests/test_report_bench_cli.py`, `backend/tests/test_report_bench_scoring.py`

**Interfaces:**
- Consumes: `classify`, `answer_lead`, `scarcity`, `LEAD_FALLBACK`, `ANSWER_FALLBACK`, `FinanceFactsGateway`, `QuestionBudgetGateway`.
- Produces: `augment_facts(facts: dict, question: str | None, finance: FinanceFactsPort, budget: QuestionBudgetPort, region: str, industry: str) -> dict` (benchmark_report, 순수에 가깝게 — 포트 주입); CLI `freeze --augment`; `answer_packets(scenario_id, question, body, answers, seed, lead: str | None = None)`.

- [ ] **Step 1: 실패하는 테스트**

`test_report_bench_cli.py`에(기존 import 스타일을 따른다):
```python
def test_facts_보강은_finance와_질문_속_예산만_더하고_나머지는_그대로_둔다():
    class Finance(FinanceFactsPort):
        def prefill(self, region_code, industry_id):
            return {"available": True}

    class Budget(QuestionBudgetPort):
        def parse(self, question):
            return 50_000_000

    facts = {"region": {"code": "1"}, "budget": None, "news": []}
    out = augment_facts(facts, "5천만 원 있는데", Finance(), Budget(), "1", "cafe")

    assert out == {"region": {"code": "1"}, "budget": 50_000_000, "news": [], "finance": {"available": True}}


def test_facts_보강은_프리필이_실패해도_그_자리만_비운다():
    class Finance(FinanceFactsPort):
        def prefill(self, region_code, industry_id):
            raise RuntimeError("없음")

    class Budget(QuestionBudgetPort):
        def parse(self, question):
            return None

    out = augment_facts({"budget": None}, None, Finance(), Budget(), "1", "cafe")
    assert out["finance"]["available"] is False and out["budget"] is None
```

`test_report_bench_scoring.py`에:
```python
def test_해석_판정_묶음은_직접_답을_모든_해석_위에_한_번_싣는다():
    packet, _ = answer_packets("e001", "대출?", "본문", {"m1": "해석1", "m2": "해석2"}, 0, lead="직접 답")
    assert packet.count("직접 답") == 1
    assert packet.index("직접 답") < packet.index("## 해석")
```

- [ ] **Step 2: 실패 확인.**

- [ ] **Step 3: 구현**
  - `benchmark_report.py`:

```python
def augment_facts(
    facts: dict, question: str | None, finance: FinanceFactsPort, budget: QuestionBudgetPort, region: str, industry: str
) -> dict:
    """얼린 facts에 v0.69.0 키만 더한다 — 나머지 키는 그대로라 이전 결과와 비교할 수 있다(설계서 §10-2)."""
    try:
        prefill = finance.prefill(region, industry)
    except Exception as error:
        prefill = {"available": False, "reason": f"{type(error).__name__}: {error}"}
    parsed = budget.parse(question) if question and facts.get("budget") is None else None
    return {**facts, "budget": facts.get("budget") if parsed is None else parsed, "finance": prefill}
```

  - `_cmd_freeze`: `args.augment`이면 기존 파일마다 `_write_json(path, augment_facts(_read_json(path), s["question"], FinanceFactsGateway(), QuestionBudgetGateway(), s["region_code"], s["industry_id"]))` 후 출력 `freeze --augment: {id}`; 아니면 기존 동작. argparse `freeze` 서브파서에 `--augment`(store_true) 추가.
  - `_cmd_sections_check`: `sections`에 직접 답을 더해 검사한다 — `topic = classify(s["question"])`; `topic is not None and scarcity(facts) is None`이면 `sections = {**sections, "answer_lead": answer_lead(facts, topic)}`. docstring "6개 절" → "6개 절과 직접 답".
  - `_first_rep_answers`: 반환을 `{sid: (body, lead, {model: answer})}`로 — body는 `answer`·`answer_lead`를 뺀 절, lead는 `r["sections"].get("answer_lead")`. `_cmd_judge_export`가 `answer_packets(sid, question, body, answers, _JUDGE_SEED, lead=lead)`로 넘긴다.
  - `score_run`: `"fallback": answer.startswith((ANSWER_FALLBACK, LEAD_FALLBACK))` (대안 안내 문장이 뒤에 붙어도 폴백으로 센다).
  - `report_bench_scoring.answer_packets`: `lead`가 있으면 본문 앞에 `["## 직접 답과 근거 (코드 — 아래 모든 해석에 공통)", "", lead, ""]`를 넣는다.
- [ ] **Step 4: 기준표 v2** — `data/eval/report_answer_rubric.md`의 `answered`·`core_error` 정의를 아래로 교체하고 맨 위에 "v2 (2026-10-06, BE v0.69.0 — 질문 직접 답 구조)" 표기:
  - `answered`: 답 상자 전체(직접 답·근거·해석)를 본다. 질문이 있으면 **질문의 구체 요소(금액·시간대·경쟁·대상 고객·대출·코로나)에 대한 근거 또는 "판단할 수 없다 + 이유"**가 있으면 true, 일반론뿐이면 false. 질문이 없으면 "이 동네에서 이 업종을 한다면 먼저 볼 것"을 짚었는가.
  - `core_error`: **해석(LLM)만** 본다. 기존 항목 그대로 + "직접 답(코드)의 결론을 뒤집거나 흐림".
  - 폴백 문장 두 개(`ANSWER_FALLBACK`, `LEAD_FALLBACK`)는 `core_error: false`; `answered`는 직접 답이 있으면 위 기준대로, 없으면 false.
- [ ] **Step 5: 확인** — `.venv/bin/python -m pytest -q` 전체 통과, `.venv/bin/python -m apps.agent.adapter.inbound.cli.benchmark_report sections-check --scenario-set 150` → 문제 0건(아직 보강 전이라 finance 줄은 자료 부족으로 나온다 — 정상).
- [ ] **Step 6: 버전 로그** — `backend/docs/backend_ver_log.md` 맨 위(기존 형식)에 `## [v0.69.0] - 2026-10-06` — Added: 질문 유형 분류기·직접 답(answer_lead)·facts.finance·질문 속 예산·주민/뉴스 줄·벤치 freeze --augment / Changed: 해석 지시(질문 있음 2~3문장)·SECTION_ORDER·폴백 문장·판정 기준표 v2.
- [ ] **Step 7: 커밋** — `git add -A backend data/eval/report_answer_rubric.md && git commit -m "backend v0.69.0: 벤치 facts 보강·직접 답 검사·판정 기준표 v2"`

---

### Task 8: 프론트 — "질문에 대한 답" 상자 (Codex 위임)

**Files (Codex가 탐색 후 확정):** `frontend/src/shared/api/types.ts`, `frontend/src/features/agent-report/components/report-view.tsx`(+ 테스트), 저장 리포트 재열람 경로, `frontend/src/app/api/mock/*`(SSE·fixtures), `frontend/docs/frontend_ver_log.md`

계약(백엔드 Task 5·6과 같다):
- `ReportSection`에 `"answer_lead"` 추가. `FactSection`은 `"answer"`와 `"answer_lead"`를 둘 다 뺀다.
- `ReportFacts`에 `finance?: { available: boolean; reason?: string; expected_monthly_revenue?: PrefillValue; rent_per_m2?: PrefillValue; loan_rate?: PrefillValue }`(선택 필드, `PrefillValue = { value: number | null; unit: string | null; basis: Record<string, unknown>; caveat: string }`). 화면에 새로 그리지는 않는다.
- SSE 순서: 질문이 있고 자료 부족 동네가 아니면 `report_delta answer_lead`가 6개 절보다 **먼저**, `answer`(LLM)는 맨 뒤.

화면:
- 리포트 맨 위 "해석" 섹션을 `answer_lead`가 있을 때 **"질문에 대한 답"** 상자로: 제목 "질문에 대한 답", `answer_lead` 마크다운(코드, 즉시 표시), 그 아래 작은 라벨 "AI 해석" + `answer`. 안내 문구는 "첫 문장과 근거는 사실에서 코드가 쓴 것이고, AI 해석은 그 이유를 풀어 쓴 것입니다."
- `answer` 도착 전에는 "AI 해석" 자리에 높이를 확보한 자리 표시(레이아웃 밀림 방지).
- `answer_lead`가 없으면(질문 없음·자료 부족·옛 저장본) 지금 화면 그대로.
- mock SSE: 요청에 질문이 있으면 `answer_lead` 조각을 먼저 내보낸다(결정적 픽스처, `Math.random` 금지). 계약 테스트로 순서를 고정.
- 버전: frontend v0.54.0 기록. 토큰 기반 스타일(하드코딩 hex 금지), 기존 테스트 전부 통과(`npm test -- --run`), `npx tsc --noEmit`, `npm run lint`.

실행: `codex exec`로 위 계약과 `CLAUDE.md` Part V를 주고 위임, 결과 diff를 검토 후 커밋 `frontend v0.54.0: 질문에 대한 답 상자(answer_lead)`.

---

### Task 9: 재평가 (컨트롤러 직접)

- [ ] `cd backend && .venv/bin/python -m apps.agent.adapter.inbound.cli.benchmark_report freeze --augment --scenario-set 150` → 150건 보강(커밋: `data/eval/report_facts_150/` 변경 — 공개 저장소, finance는 공개 통계라 문제없음).
- [ ] `sections-check --scenario-set 150` → 문제 0.
- [ ] `run --scenario-set 150 --cache-tag topic150` (Gemini·gemma4:12b), `score` 같은 태그.
- [ ] `judge-export --scenario-set 150 --cache-tag topic150` → 묶음을 Claude(opus) 서브에이전트가 기준표 v2로 블라인드 판정 → `judge-import`. 116건(자료 부족 제외) 핵심 오류율·95% 구간 산출, 이전(Gemini 17.2%·12b 37.9%)과 비교.
- [ ] 사람 검수 3차 화면(비공개 artifact + db): 2차 표본 중 질문 있는 16건(e011·e025·e067·e073·e080·e092·e104·e108·e123 등 — `judge-codefirst150c/human_sample.json`과 2차 결과에서 질문 있는 것), Gemini 하나, 항목 "질문에 답했나(예/아니오)+메모".
- [ ] 결과 노트 `data/eval/results/question-answer-2026-10-06/notes.md`, HANDOFF §0-14 갱신, 커밋.
