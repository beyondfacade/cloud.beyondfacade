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
