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
