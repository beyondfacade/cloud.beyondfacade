"""LLMGatewayPort.stream() 어댑터 검증 — Gemini SDK 스텁·Ollama MockTransport (네트워크 없음)."""

import json

import httpx
import pytest
from google.genai import errors

from apps.agent.adapter.outbound.llm import gemini_llm_adapter
from apps.agent.adapter.outbound.llm.gemini_llm_adapter import GeminiLLMAdapter
from apps.agent.adapter.outbound.llm.ollama_llm_adapter import OllamaLLMAdapter
from apps.agent.app.ports.output.agent_port import LLMToolSpec


# --- Ollama ---


def _ndjson(lines: list[dict]) -> bytes:
    return "\n".join(json.dumps(line, ensure_ascii=False) for line in lines).encode("utf-8")


def _stream_transport(captured, lines: list[dict]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(200, content=_ndjson(lines))

    return httpx.MockTransport(handler)


def test_ollama_stream은_NDJSON_조각을_순서대로_흘린다():
    captured: list[dict] = []
    adapter = OllamaLLMAdapter(
        transport=_stream_transport(
            captured,
            [
                {"message": {"content": "[SECTION:"}},
                {"message": {"content": "verdict]🔴"}},
                {"message": {"content": ""}, "done": True, "prompt_eval_count": 11, "eval_count": 3},
            ],
        )
    )

    events = list(adapter.stream([{"role": "user", "content": "써줘"}], []))

    assert captured[0]["stream"] is True
    assert [event.text for event in events if event.kind == "text"] == ["[SECTION:", "verdict]🔴"]
    assert events[-2].kind == "tool_calls" and events[-2].tool_calls == []
    assert (events[-1].usage.input_tokens, events[-1].usage.output_tokens) == (11, 3)


def test_ollama_stream의_도구_호출은_마지막_메시지로_온다():
    captured: list[dict] = []
    adapter = OllamaLLMAdapter(
        transport=_stream_transport(
            captured,
            [
                {"message": {"content": "찾아보겠습니다"}},
                {
                    "message": {
                        "content": "",
                        "tool_calls": [{"function": {"name": "search_news", "arguments": {"q": "한식"}}}],
                    },
                    "done": True,
                },
            ],
        )
    )
    tool = LLMToolSpec(name="search_news", description="뉴스", input_schema={"type": "object"})

    events = list(adapter.stream([{"role": "user", "content": "써줘"}], [tool]))

    assert captured[0]["tools"][0]["function"]["name"] == "search_news"
    calls = events[-2].tool_calls
    assert [(call.tool_name, call.arguments) for call in calls] == [("search_news", {"q": "한식"})]


# --- Gemini ---


class _StubUsage:
    def __init__(self, prompt: int, candidates: int) -> None:
        self.prompt_token_count = prompt
        self.candidates_token_count = candidates


class _StubCall:
    def __init__(self, name: str, args: dict) -> None:
        self.name = name
        self.args = args


class _StubChunk:
    def __init__(self, text: str | None = None, function_calls=None, usage=None) -> None:
        self.text = text
        self.function_calls = function_calls
        self.usage_metadata = usage


class _StubModels:
    """generate_content_stream 스텁 — 대본을 순서대로 낸다(대본이 예외면 던진다)."""

    def __init__(self, scripts: list) -> None:
        self._scripts = list(scripts)
        self.calls: list[dict] = []

    def generate_content_stream(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents})
        script = self._scripts.pop(0)
        if isinstance(script, Exception):
            raise script
        return iter(script)


@pytest.fixture
def gemini(monkeypatch):
    """genai.Client를 스텁으로 갈아끼운 어댑터 팩토리 — 키도 네트워크도 필요 없다."""

    def build(scripts: list) -> tuple[GeminiLLMAdapter, _StubModels]:
        models = _StubModels(scripts)
        monkeypatch.setattr(
            gemini_llm_adapter.genai, "Client", lambda **kwargs: type("C", (), {"models": models})()
        )
        monkeypatch.setattr(gemini_llm_adapter.time, "sleep", lambda seconds: None)
        return GeminiLLMAdapter(api_key="stub-key"), models

    return build


def test_gemini_stream은_조각을_순서대로_내고_도구_호출과_usage는_끝에_온다(gemini):
    adapter, _ = gemini(
        [
            [
                _StubChunk(text="[SECTION:verdict]"),
                _StubChunk(text="🔴 비추천."),
                _StubChunk(
                    function_calls=[_StubCall("search_news", {"q": "한식"})],
                    usage=_StubUsage(120, 40),
                ),
            ]
        ]
    )

    events = list(adapter.stream([{"role": "user", "content": "써줘"}], []))

    assert [event.kind for event in events] == ["text", "text", "tool_calls", "usage"]
    assert [event.text for event in events[:2]] == ["[SECTION:verdict]", "🔴 비추천."]
    assert [(c.tool_name, c.arguments) for c in events[2].tool_calls] == [("search_news", {"q": "한식"})]
    assert (events[3].usage.input_tokens, events[3].usage.output_tokens) == (120, 40)


def test_gemini_stream은_첫_조각_전_429만_재시도한다(gemini):
    """이미 흘려보낸 글을 처음부터 다시 쓰게 하지 않는다 — 재시도는 첫 조각 전까지다."""
    adapter, models = gemini(
        [errors.ClientError(429, {"message": "quota"}), [_StubChunk(text="다시 씁니다")]]
    )

    events = list(adapter.stream([{"role": "user", "content": "써줘"}], []))

    assert len(models.calls) == 2
    assert [event.text for event in events if event.kind == "text"] == ["다시 씁니다"]


def test_gemini_stream은_첫_조각_뒤_실패를_그대로_올린다(gemini):
    def exploding():
        yield _StubChunk(text="반쯤 쓴 글")
        raise errors.ClientError(429, {"message": "quota"})

    adapter, _ = gemini([exploding()])

    events = []
    with pytest.raises(errors.ClientError):
        for event in adapter.stream([{"role": "user", "content": "써줘"}], []):
            events.append(event)

    assert [event.text for event in events] == ["반쯤 쓴 글"]


def test_gemini_stream은_빈_스트림도_계약을_지킨다(gemini):
    """조각이 하나도 없어도 tool_calls·usage 두 이벤트는 나온다(호출부가 턴을 닫을 수 있어야 한다)."""
    adapter, _ = gemini([[]])

    events = list(adapter.stream([{"role": "user", "content": "써줘"}], []))

    assert [event.kind for event in events] == ["tool_calls", "usage"]
    assert events[0].tool_calls == []
