"""FallbackLLMAdapter 검증 — primary 실패 시에만 secondary로 내려간다 (네트워크 없음)."""

import pytest

from apps.agent.adapter.outbound.llm.fallback_llm_adapter import FallbackLLMAdapter
from apps.agent.app.ports.output.agent_port import (
    LLMGatewayPort,
    LLMToolCall,
    LLMTurn,
    LLMUsage,
)


class FakeLLM(LLMGatewayPort):
    def __init__(self, name: str, error: Exception | None = None) -> None:
        self.model_name = name
        self._error = error
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
