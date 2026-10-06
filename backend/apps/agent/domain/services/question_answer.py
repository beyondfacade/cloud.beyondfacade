"""질문에 대한 직접 답(첫 문장)과 근거 줄 — facts만으로 쓰는 순수 모듈 (stdlib만).

설계서 docs/superpowers/specs/2026-10-05-question-answer-design.md §5. 결론은 틀리면 안 되므로 코드가 쓰고,
LLM은 그 아래 해석만 쓴다. report_sections의 원칙(숫자에 범위·자료 부족은 이유와 함께·태그는 코드)을 따른다.
유형마다 Strategy 하나 — 첫 문장의 머리말·꼬리와 근거 줄만 다르다.
"""

import logging
import re
from abc import ABC, abstractmethod

from apps.agent.domain.services.question_topic import QuestionTopic
from apps.agent.domain.services.report_sections import (
    DISASTER_NOTE,
    FACT,
    HOUR_BAND_LABELS,
    SIGNAL_LABELS,
    current_year,
    missing,
    missing_reason,
    quarter_label,
    resident_line,
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
    "weekday": "평일",
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
        f"점포 {basis.get('store_count')}곳 평균): 약 {round(item['value'] / 10_000):,}만 원 — {item.get('caveat')}"
    )


def rent_line(facts: dict) -> str:
    region, _ = subject_names(facts)
    item, reason = _finance_item(facts, "rent_per_m2")
    if item is None:
        return f"{FACT} 상가 임대료({region}): {missing(reason)}"
    basis = item.get("basis") or {}
    path = str(basis.get("region_path") or "").replace(">", " ")
    period = str(basis.get("period") or "")
    when = f"{period[:4]}년 {period[5:]}분기" if re.fullmatch(r"\d{4}Q\d", period) else period
    # 값 단위는 천원/㎡/월 — 만 원으로 쓴다
    return f"{FACT} 상가 임대료({path} 권역, {when}): ㎡당 월 약 {item['value'] / 10:.1f}만 원 — {item.get('caveat')}"


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


# 시간당 하루 평균 대비 배수 → 낱말. 숫자만 주면 LLM이 0.97배를 "평균보다 높다"로, 사람 흐름과 매출을 섞어 옮긴다
_INTENSITY_WORDS = (
    (1.5, "하루 평균보다 크게 많음"),
    (1.1, "하루 평균보다 많음"),
    (0.9, "하루 평균과 비슷"),
    (0.5, "하루 평균보다 적음"),
)


def intensity_word(value: float) -> str:
    """위에서부터 처음 넘는 경계의 낱말, 다 못 넘으면 절반 미만."""
    return next((word for floor, word in _INTENSITY_WORDS if value >= floor), "하루 평균의 절반 미만")


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
        f"사람 흐름은 {intensity_word(bands[code]['footfall_intensity'])}"
        f"(시간당 하루 평균의 {bands[code]['footfall_intensity']:.2f}배). "
        f"매출은 {intensity_word(bands[code]['sales_intensity'])}({bands[code]['sales_intensity']:.2f}배)."
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


_HOURS_EVIDENCE = {"weekend": _weekend_lines, "weekday": _weekend_lines}  # 주말÷평일 비 한 줄이 둘 다 답한다  # 나머지 구간은 _band_lines


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


# 유형 → Strategy
_ANSWERS: dict[str, TopicAnswer] = {
    "general": GeneralAnswer(),
    "budget": BudgetAnswer(),
    "loan": LoanAnswer(),
    "hours": HoursAnswer(),
    "competition": CompetitionAnswer(),
    "customers": CustomersAnswer(),
    "covid": CovidAnswer(),
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
