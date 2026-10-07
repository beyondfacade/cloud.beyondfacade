"""부하 테스트용 가짜 LLM (testplan §7-4 (c)) — 고정 시간만 쉬고 고정 값을 낸다. 실제로 기다리지 않는다."""

from apps.agent.adapter.outbound.llm.fixed_delay_llm_adapter import FixedDelayLLMAdapter
from apps.agent.dependencies.analysis_dependencies import build_analysis_use_case
from apps.intent.adapter.outbound.llm.fixed_delay_intent_llm_adapter import FixedDelayIntentLlmAdapter
from core.matrix.grid_keymaker_secret_manager import get_settings


def test_가짜_해석_LLM은_정해진_시간을_쉰_뒤_고정_문장을_낸다():
    waits: list[float] = []
    turn = FixedDelayLLMAdapter(delay_seconds=3.0, sleep=waits.append).chat([], [])
    assert waits == [3.0]
    assert turn.text and turn.tool_calls == []


def test_가짜_의도_LLM은_정해진_시간을_쉰_뒤_제안_없음을_낸다():
    waits: list[float] = []
    assert FixedDelayIntentLlmAdapter(delay_seconds=3.0, sleep=waits.append).extract("서교동 카페") is None
    assert waits == [3.0]


def test_LLM_MODE가_fake면_요청이_hybrid를_골라도_분석이_가짜_LLM을_쓴다(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "fake")
    get_settings.cache_clear()
    try:
        assert build_analysis_use_case("hybrid").myself()["model"] == "fake"
    finally:
        monkeypatch.delenv("LLM_MODE")
        get_settings.cache_clear()
