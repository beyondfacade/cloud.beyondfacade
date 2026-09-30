"""FallbackLLMAdapter 검증 — primary 실패 시에만 secondary로 내려간다 (네트워크 없음)."""

import pytest

from apps.agent.adapter.outbound.llm.fallback_llm_adapter import FallbackLLMAdapter
from apps.agent.app.ports.output.agent_port import (
    LLMGatewayPort,
    LLMStreamEvent,
    LLMToolCall,
    LLMTurn,
    LLMUsage,
)
from apps.agent.app.ports.output.llm_call_port import LlmCallRecorderPort
from apps.agent.domain.entities.llm_call_entity import LlmCall, LlmCallOutcome


class FakeLLM(LLMGatewayPort):
    def __init__(self, name: str, error: Exception | None = None, after: int = 0) -> None:
        """`error`가 있으면 텍스트 조각 `after`개를 낸 뒤 던진다 (0이면 첫 조각 전 실패)."""
        self.model_name = name
        self._error = error
        self._after = after
        self.calls = 0

    def chat(self, messages, tools) -> LLMTurn:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return LLMTurn(
            text=f"{self.model_name} 응답",
            tool_calls=[LLMToolCall(tool_name="t", arguments={})],
            usage=LLMUsage(input_tokens=1, output_tokens=2),
        )

    def stream(self, messages, tools):
        self.calls += 1
        for index in range(self._after):
            yield LLMStreamEvent(kind="text", text=f"{self.model_name} 조각{index}")
        if self._error is not None:
            raise self._error
        yield LLMStreamEvent(kind="text", text=f"{self.model_name} 응답")
        yield LLMStreamEvent(kind="tool_calls", tool_calls=[])
        yield LLMStreamEvent(kind="usage", usage=LLMUsage(input_tokens=1, output_tokens=2))


def _adapter(primary, secondary) -> FallbackLLMAdapter:
    return FallbackLLMAdapter(primary=lambda: primary, secondary=lambda: secondary)


def test_primary가_성공하면_secondary를_부르지_않는다():
    primary, secondary = FakeLLM("gemini-2.5-flash"), FakeLLM("gemma4:12b")

    turn = _adapter(primary, secondary).chat([], [])

    assert turn.text == "gemini-2.5-flash 응답"
    assert (primary.calls, secondary.calls) == (1, 0)


def test_primary가_성공하면_model_name이_primary다():
    adapter = _adapter(FakeLLM("gemini-2.5-flash"), FakeLLM("gemma4:12b"))

    adapter.chat([], [])

    # 라우터가 run 이후 _llm.model_name을 읽어 llm_usage에 기록한다
    assert adapter.model_name == "gemini-2.5-flash"


def test_primary가_예외면_secondary가_답하고_model_name이_secondary다():
    primary = FakeLLM("gemini-2.5-flash", error=RuntimeError("429"))
    secondary = FakeLLM("gemma4:12b")
    adapter = _adapter(primary, secondary)

    turn = adapter.chat([], [])

    assert turn.text == "gemma4:12b 응답"
    assert (primary.calls, secondary.calls) == (1, 1)
    assert adapter.model_name == "gemma4:12b"


def test_키가_없어_primary_생성이_실패하면_바로_secondary로_간다():
    secondary = FakeLLM("gemma4:12b")

    def no_key() -> LLMGatewayPort:
        raise ValueError("GEMINI_API_KEY 미설정")

    adapter = FallbackLLMAdapter(primary=no_key, secondary=lambda: secondary)
    turn = adapter.chat([], [])

    assert turn.text == "gemma4:12b 응답"
    assert secondary.calls == 1
    assert adapter.model_name == "gemma4:12b"


def test_생성이_한번_실패하면_다음_턴에_다시_시도하지_않는다():
    """턴마다 키 없는 클라이언트를 만들며 실패를 반복하지 않는다."""
    attempts = []
    secondary = FakeLLM("gemma4:12b")

    def no_key() -> LLMGatewayPort:
        attempts.append(1)
        raise ValueError("GEMINI_API_KEY 미설정")

    adapter = FallbackLLMAdapter(primary=no_key, secondary=lambda: secondary)
    adapter.chat([], [])
    adapter.chat([], [])

    assert len(attempts) == 1
    assert secondary.calls == 2


def test_둘_다_실패하면_secondary의_예외를_올린다():
    primary = FakeLLM("gemini-2.5-flash", error=RuntimeError("429"))
    secondary = FakeLLM("gemma4:12b", error=RuntimeError("ollama 꺼짐"))

    with pytest.raises(RuntimeError, match="ollama 꺼짐"):
        _adapter(primary, secondary).chat([], [])


def test_polling_중_primary가_회복되면_다시_primary를_쓴다():
    """폴백은 그 턴만이다 — 다음 턴은 primary부터 다시 시도한다."""
    calls = {"n": 0}

    class Flaky(FakeLLM):
        def chat(self, messages, tools):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("일시 장애")
            return LLMTurn(text="회복", tool_calls=[], usage=LLMUsage(0, 0))

    primary, secondary = Flaky("gemini-2.5-flash"), FakeLLM("gemma4:12b")
    adapter = _adapter(primary, secondary)

    assert adapter.chat([], []).text == "gemma4:12b 응답"
    assert adapter.chat([], []).text == "회복"
    assert adapter.model_name == "gemini-2.5-flash"


# --- 스트림 폴백 (설계서 §3-4) ---


def test_스트림이_정상이면_primary만_쓰고_model_name도_primary다():
    primary, secondary = FakeLLM("gemini-2.5-flash"), FakeLLM("gemma4:12b")
    adapter = _adapter(primary, secondary)

    events = list(adapter.stream([], []))

    assert [event.text for event in events if event.kind == "text"] == ["gemini-2.5-flash 응답"]
    assert (primary.calls, secondary.calls) == (1, 0)
    assert adapter.model_name == "gemini-2.5-flash"


def test_첫_조각_전에_터지면_secondary가_이어받는다():
    primary = FakeLLM("gemini-2.5-flash", error=RuntimeError("429"))
    secondary = FakeLLM("gemma4:12b")
    adapter = _adapter(primary, secondary)

    events = list(adapter.stream([], []))

    assert [event.text for event in events if event.kind == "text"] == ["gemma4:12b 응답"]
    assert (primary.calls, secondary.calls) == (1, 1)
    assert adapter.model_name == "gemma4:12b"


def test_첫_조각_뒤에_터지면_예외를_그대로_올린다():
    """반쯤 쓴 글을 다른 모델이 이어 쓰지 않는다 — 인터랙터가 폴백 섹션으로 마무리한다."""
    primary = FakeLLM("gemini-2.5-flash", error=RuntimeError("연결 끊김"), after=1)
    secondary = FakeLLM("gemma4:12b")
    adapter = _adapter(primary, secondary)

    seen = []
    with pytest.raises(RuntimeError, match="연결 끊김"):
        for event in adapter.stream([], []):
            seen.append(event.text)

    assert seen == ["gemini-2.5-flash 조각0"]
    assert secondary.calls == 0


def test_키가_없으면_스트림도_바로_secondary로_간다():
    secondary = FakeLLM("gemma4:12b")

    def no_key() -> LLMGatewayPort:
        raise ValueError("GEMINI_API_KEY 미설정")

    adapter = FallbackLLMAdapter(primary=no_key, secondary=lambda: secondary)
    events = list(adapter.stream([], []))

    assert [event.text for event in events if event.kind == "text"] == ["gemma4:12b 응답"]
    assert adapter.model_name == "gemma4:12b"


# --- 호출 결과 기록 (헬스케어실 폴백률·오류율의 원천) ---


class MemoryRecorder(LlmCallRecorderPort):
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[LlmCall] = []
        self._fail = fail

    def record(self, call: LlmCall) -> None:
        if self._fail:
            raise RuntimeError("DB 끊김")
        self.calls.append(call)


def _recorded(primary, secondary, recorder) -> FallbackLLMAdapter:
    return FallbackLLMAdapter(primary=lambda: primary, secondary=lambda: secondary, recorder=recorder)


def test_primary_성공은_ok_한_건으로_남는다():
    recorder = MemoryRecorder()
    _recorded(FakeLLM("gemini-2.5-flash"), FakeLLM("gemma4:12b"), recorder).chat([], [])
    assert [(c.model, c.outcome) for c in recorder.calls] == [("gemini-2.5-flash", LlmCallOutcome.OK)]
    assert recorder.calls[0].latency_ms >= 0


def test_primary_실패는_fallback과_secondary_ok로_남고_예외_종류만_기록한다():
    recorder = MemoryRecorder()
    primary = FakeLLM("gemini-2.5-flash", error=RuntimeError("key=AIza-secret 429"))
    _recorded(primary, FakeLLM("gemma4:12b"), recorder).chat([], [])
    assert [(c.model, c.outcome, c.error_kind) for c in recorder.calls] == [
        ("gemini-2.5-flash", LlmCallOutcome.FALLBACK, "RuntimeError"),
        ("gemma4:12b", LlmCallOutcome.OK, None),
    ]


def test_둘_다_실패하면_마지막은_error로_남고_예외가_올라간다():
    recorder = MemoryRecorder()
    adapter = _recorded(FakeLLM("g", error=RuntimeError("a")), FakeLLM("l", error=TimeoutError("b")), recorder)
    with pytest.raises(TimeoutError):
        adapter.chat([], [])
    assert [c.outcome for c in recorder.calls] == [LlmCallOutcome.FALLBACK, LlmCallOutcome.ERROR]
    assert recorder.calls[-1].error_kind == "TimeoutError"


def test_기록이_실패해도_LLM_호출은_성공한다():
    turn = _recorded(FakeLLM("gemini-2.5-flash"), FakeLLM("gemma4:12b"), MemoryRecorder(fail=True)).chat([], [])
    assert turn.text == "gemini-2.5-flash 응답"


def test_스트림도_끝까지_받으면_ok_첫_조각_전_실패는_fallback으로_남는다():
    recorder = MemoryRecorder()
    primary = FakeLLM("gemini-2.5-flash", error=RuntimeError("x"))
    list(_recorded(primary, FakeLLM("gemma4:12b"), recorder).stream([], []))
    assert [(c.model, c.outcome) for c in recorder.calls] == [
        ("gemini-2.5-flash", LlmCallOutcome.FALLBACK),
        ("gemma4:12b", LlmCallOutcome.OK),
    ]


def test_스트림이_쓰다가_끊기면_error로_남는다():
    recorder = MemoryRecorder()
    primary = FakeLLM("gemini-2.5-flash", error=RuntimeError("끊김"), after=1)
    with pytest.raises(RuntimeError):
        list(_recorded(primary, FakeLLM("gemma4:12b"), recorder).stream([], []))
    assert [c.outcome for c in recorder.calls] == [LlmCallOutcome.ERROR]


def test_llm_call_event_테이블에_기록된다():
    from sqlalchemy import text

    from apps.agent.adapter.outbound.repositories.llm_call_repository import SqlAlchemyLlmCallRecorder
    from core.matrix.grid_oracle_database_manager import session_scope

    with session_scope() as session:
        session.execute(text("truncate llm_call_event"))
    _recorded(FakeLLM("g", error=ValueError("x")), FakeLLM("l"), SqlAlchemyLlmCallRecorder()).chat([], [])
    with session_scope() as session:
        rows = session.execute(text("select model, outcome, error_kind from llm_call_event order by id")).all()
    assert [tuple(row) for row in rows] == [("g", "fallback", "ValueError"), ("l", "ok", None)]


# --- Composition Root 배선 (설계 결정: 기본이 hybrid) ---


def test_레지스트리가_hybrid를_기본으로_하고_단일_모델도_남긴다():
    from apps.agent.dependencies.analysis_dependencies import _LLM_REGISTRY

    # gemma3·gemini 직접 지정은 두뇌 비교 평가 러너(run_agent_eval --model)가 쓴다
    assert set(_LLM_REGISTRY) == {"hybrid", "gemma3", "gemini"}


def test_hybrid_팩토리가_폴백_어댑터를_만든다():
    from apps.agent.dependencies.analysis_dependencies import _LLM_REGISTRY

    assert isinstance(_LLM_REGISTRY["hybrid"](), FallbackLLMAdapter)


def test_요청_스키마의_기본_모델이_hybrid다():
    from apps.agent.adapter.inbound.api.schemas.analysis_schema import (
        AnalysisCreateRequest,
    )

    body = AnalysisCreateRequest(region="1168064000", industry="cafe")

    assert body.model == "hybrid"
    with pytest.raises(ValueError):
        AnalysisCreateRequest(region="1168064000", industry="cafe", model="gpt")
