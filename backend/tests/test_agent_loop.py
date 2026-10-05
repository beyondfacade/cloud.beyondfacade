"""analysis_interactor — 사실은 코드, 해석은 LLM 한 단락: SSE 이벤트 계약 (FakeLLM, DB·네트워크 없음)."""

import json
from pathlib import Path

from apps.agent.adapter.outbound.llm.fallback_llm_adapter import FallbackLLMAdapter
from apps.agent.app.ports.output.agent_port import LLMGatewayPort, LLMTurn, LLMUsage
from apps.agent.app.use_cases.analysis_interactor import ANSWER_FALLBACK, SYSTEM_PROMPT, AnalysisInteractor
from apps.agent.app.use_cases.report_facts import ReportFactsCollector
from apps.agent.domain.entities.agent_event_entity import AgentEvent
from apps.agent.domain.services.report_sections import SECTION_TITLES, build_sections

# 평가셋 고정 facts — 송정동 한식, 판정 red(비추천)
_FACTS = json.loads(
    (Path(__file__).resolve().parents[2] / "data/eval/report_facts_150/e001.json").read_text(encoding="utf-8")
)
_ANSWER = "이 동네 한식은 문을 닫는 가게가 여는 가게보다 많습니다. 서두르기보다 대안 업종을 먼저 보세요."

_SIGNATURE_FIELDS = {
    "agent_status": ("agent", "status"),
    "facts": (),
    "report_delta": ("section",),
    "report_done": (),
}


def _signature(event: AgentEvent) -> tuple:
    """이벤트를 (type, 식별 필드…) 튜플로 축약 — 순서 계약 비교용."""
    return (event.type, *(event.payload[field] for field in _SIGNATURE_FIELDS[event.type]))


class FakeLLM(LLMGatewayPort):
    """답 스크립트를 순서대로 돌려주는 대역 — 예외를 넣으면 그 호출에서 던진다. 호출 인자를 기록한다."""

    def __init__(self, replies: list, model_name: str = "fake-llm") -> None:
        self.model_name = model_name
        self._replies = list(replies)
        self.calls: list[tuple[list[dict], list]] = []

    def chat(self, messages, tools):
        self.calls.append((messages, tools))
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return LLMTurn(text=reply, tool_calls=[], usage=LLMUsage(input_tokens=30, output_tokens=7))

    def stream(self, messages, tools):
        raise AssertionError("해석은 모았다가 한 번에 낸다 — stream을 쓰지 않는다")


class FakeFactsCollector(ReportFactsCollector):
    """수집 결과를 고정하는 대역 (포트 조립 없이)."""

    def __init__(self) -> None:
        pass

    def collect(self, region, industry, budget=None, question=None) -> dict:
        return _FACTS


def _run(llm, question=None, retry_llm=None) -> tuple[AnalysisInteractor, list[AgentEvent]]:
    interactor = AnalysisInteractor(llm=llm, facts=FakeFactsCollector(), retry_llm=retry_llm)
    return interactor, list(interactor.run("1120072000", "korean_food", question))


def _deltas(events: list[AgentEvent]) -> dict[str, str]:
    return {e.payload["section"]: e.payload["markdown"] for e in events if e.type == "report_delta"}


def test_이벤트_순서는_사실_코드_여섯_절_해석_완료다():
    _, events = _run(FakeLLM([_ANSWER]))

    assert [_signature(e) for e in events] == [
        ("agent_status", "orchestrator", "running"),
        ("agent_status", "facts", "running"),
        ("facts",),
        ("agent_status", "facts", "done"),
        ("agent_status", "writer", "running"),
        *(("report_delta", name) for name in SECTION_TITLES),
        ("report_delta", "answer"),
        ("agent_status", "writer", "done"),
        ("agent_status", "orchestrator", "done"),
        ("report_done",),
    ]
    deltas = _deltas(events)
    assert {name: deltas[name] for name in SECTION_TITLES} == build_sections(_FACTS)
    assert deltas["answer"] == _ANSWER


def test_LLM에는_사실_JSON이_아니라_질문과_코드가_쓴_절만_간다():
    llm = FakeLLM([_ANSWER])

    _run(llm, question="여기서 한식 해도 될까요?")

    [(messages, tools)] = llm.calls
    user = messages[1]["content"]
    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert tools == []
    assert "사용자 질문: 여기서 한식 해도 될까요?" in user
    assert build_sections(_FACTS)["reasons"] in user
    assert '"verdict_code"' not in user  # 원본 facts JSON은 넘기지 않는다


def test_질문이_없으면_총평을_요청한다():
    llm = FakeLLM([_ANSWER])

    _run(llm)

    assert "총평" in llm.calls[0][0][1]["content"]


def test_숫자가_든_문장은_해석에서_지운다():
    _, events = _run(FakeLLM(["폐업이 개업보다 많습니다. 폐업률은 31%입니다. 대안 업종을 먼저 보세요."]))

    assert _deltas(events)["answer"] == "폐업이 개업보다 많습니다. 대안 업종을 먼저 보세요."


def test_판정과_모순되면_다음_모델이_다시_쓴다():
    first = FakeLLM(["판정은 **경고 없음**입니다. 해 볼 만합니다."], "gemini-2.5-flash")
    second = FakeLLM([_ANSWER], "gemma4:12b")

    interactor, events = _run(first, retry_llm=second)

    assert _deltas(events)["answer"] == _ANSWER
    assert [a["model"] for a in interactor.last_answer_attempts] == ["gemini-2.5-flash", "gemma4:12b"]
    assert interactor.last_answer_attempts[0]["contradiction"] == "판정은 **경고 없음"
    assert interactor.last_usage == LLMUsage(input_tokens=60, output_tokens=14)  # 시도마다 누적


def test_모든_모델이_실패하면_코드_한_줄로_맺는다():
    first = FakeLLM([RuntimeError("429")], "gemini-2.5-flash")
    second = FakeLLM(["매출은 1,200만원입니다."], "gemma4:12b")  # 가드 뒤 빈 단락

    interactor, events = _run(first, retry_llm=second)

    assert _deltas(events)["answer"] == ANSWER_FALLBACK
    assert events[-1].type == "report_done"
    assert interactor.last_answer_attempts[0]["error"] == "RuntimeError: 429"


def test_hybrid가_Gemini와_로컬_모두_실패하면_로컬을_다시_부르지_않는다():
    hybrid = FallbackLLMAdapter(
        primary=lambda: FakeLLM([RuntimeError("429")], "gemini-2.5-flash"),
        secondary=lambda: FakeLLM([TimeoutError("timeout")], "gemma4:12b"),
    )
    retry = FakeLLM([], "gemma4:12b")

    interactor, events = _run(hybrid, retry_llm=retry)

    assert _deltas(events)["answer"] == ANSWER_FALLBACK and retry.calls == []
    assert [a["model"] for a in interactor.last_answer_attempts] == ["gemma4:12b"]


def test_첫_모델이_이미_로컬로_답했으면_로컬을_다시_부르지_않는다():
    """hybrid가 Gemini 장애로 로컬에 내려갔다면 model_name이 같다 — 온도 0이라 다시 불러도 같은 답이다."""
    first = FakeLLM(["판정은 **경고 없음**입니다."], "gemma4:12b")
    second = FakeLLM([], "gemma4:12b")

    _, events = _run(first, retry_llm=second)

    assert _deltas(events)["answer"] == ANSWER_FALLBACK and second.calls == []


def test_인용은_사실_묶음의_뉴스로_만든다():
    _, events = _run(FakeLLM([_ANSWER]))

    first_news = _FACTS["news"][0]
    assert events[-1].payload["citations"][0] == {
        "title": first_news["content"].split("\n")[0],
        "url": first_news["url"],
        "grade": "signal",
    }


def test_시스템_프롬프트가_숫자와_등급_변경과_추정을_금지한다():
    for phrase in ("3~5문장", "숫자를 쓰지 않는다", "판정 등급을 바꾸거나", "자료가 부족해 판단할 수 없다", "대출 중개"):
        assert phrase in SYSTEM_PROMPT


def test_운영_hybrid만_로컬_재시도를_붙인다():
    from apps.agent.dependencies.analysis_dependencies import build_analysis_use_case

    assert build_analysis_use_case("hybrid")._retry_llm.model_name == "gemma4:12b"
    assert build_analysis_use_case("gemma3")._retry_llm is None
