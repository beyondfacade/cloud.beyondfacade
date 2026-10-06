"""OllamaLLMAdapter·GeminiLLMAdapter 검증 — httpx.MockTransport 및 변환 함수 단위 테스트."""

import json

import httpx
import pytest

from apps.agent.adapter.outbound.llm.ollama_llm_adapter import OllamaLLMAdapter
from apps.agent.app.ports.output.agent_port import LLMToolSpec


def _transport(captured, response_json):
    """MockTransport: /api/chat 요청 바디 캡처 후 고정 응답 반환."""

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=response_json)

    return httpx.MockTransport(handler)


def test_ollama_chat_includes_tools_in_request_body():
    """tools가 요청 바디의 tools 필드에 포함된다."""
    captured = []
    adapter = OllamaLLMAdapter(
        transport=_transport(
            captured,
            {"message": {"content": "안녕", "tool_calls": []}},
        )
    )
    tool = LLMToolSpec(
        name="search_shop",
        description="상점 검색",
        input_schema={"type": "object", "properties": {}},
    )

    adapter.chat(messages=[{"role": "user", "content": "안녕"}], tools=[tool])

    assert captured[0]["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "search_shop",
                "description": "상점 검색",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    assert captured[0]["model"] == "gemma3:12b"
    assert captured[0]["stream"] is False


def test_ollama_chat_parses_tool_calls_from_response():
    """응답의 message.tool_calls → LLMToolCall 리스트로 파싱된다."""
    captured = []
    adapter = OllamaLLMAdapter(
        transport=_transport(
            captured,
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "search_shop",
                                "arguments": {"query": "카페"},
                            }
                        }
                    ],
                },
                "prompt_eval_count": 12,
                "eval_count": 5,
            },
        )
    )

    turn = adapter.chat(messages=[{"role": "user", "content": "카페 찾아줘"}], tools=[])

    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0].tool_name == "search_shop"
    assert turn.tool_calls[0].arguments == {"query": "카페"}
    assert turn.usage.input_tokens == 12
    assert turn.usage.output_tokens == 5


def test_ollama_chat_without_tool_calls_returns_text_turn():
    """tool_calls가 없는 응답은 text 턴으로 반환되며 tool_calls는 빈 리스트."""
    captured = []
    adapter = OllamaLLMAdapter(
        transport=_transport(
            captured,
            {"message": {"content": "안녕하세요"}},
        )
    )

    turn = adapter.chat(messages=[{"role": "user", "content": "안녕"}], tools=[])

    assert turn.text == "안녕하세요"
    assert turn.tool_calls == []
    assert turn.usage.input_tokens == 0
    assert turn.usage.output_tokens == 0


def test_gemini_message_role_mapping():
    """메시지 role 매핑: system→system_instruction 분리, user→user, assistant→model, tool→functionResponse."""
    from apps.agent.adapter.outbound.llm.gemini_llm_adapter import to_gemini_contents

    messages = [
        {"role": "system", "content": "너는 상점 안내 봇이다."},
        {"role": "user", "content": "카페 추천해줘"},
        {"role": "assistant", "content": "네, 찾아볼게요"},
        {"role": "tool", "content": '{"store_count": 10}', "tool_name": "search_shop"},
    ]

    system_instruction, contents = to_gemini_contents(messages)

    assert system_instruction == "너는 상점 안내 봇이다."
    assert contents[0]["role"] == "user"
    assert contents[0]["parts"][0]["text"] == "카페 추천해줘"
    assert contents[1]["role"] == "model"
    assert contents[1]["parts"][0]["text"] == "네, 찾아볼게요"
    assert contents[2]["parts"][0]["functionResponse"] == {
        "name": "search_shop",
        "response": {"result": '{"store_count": 10}'},
    }


def test_gemini_tool_spec_to_function_declarations():
    """LLMToolSpec → function_declarations dict 변환."""
    from apps.agent.adapter.outbound.llm.gemini_llm_adapter import to_function_declarations
    from apps.agent.app.ports.output.agent_port import LLMToolSpec

    tools = [
        LLMToolSpec(
            name="search_shop",
            description="상점 검색",
            input_schema={"type": "object", "properties": {}},
        )
    ]

    declarations = to_function_declarations(tools)

    assert declarations == [
        {
            "name": "search_shop",
            "description": "상점 검색",
            "parameters": {"type": "object", "properties": {}},
        }
    ]


def test_anthropic_메시지는_system을_분리하고_user_assistant만_남긴다():
    from apps.agent.adapter.outbound.llm.anthropic_llm_adapter import to_anthropic_messages

    system, messages = to_anthropic_messages(
        [
            {"role": "system", "content": "규칙 1"},
            {"role": "system", "content": "규칙 2"},
            {"role": "user", "content": "질문"},
            {"role": "assistant", "content": "답"},
        ]
    )

    assert system == "규칙 1\n규칙 2"
    assert messages == [{"role": "user", "content": "질문"}, {"role": "assistant", "content": "답"}]


def test_anthropic_어댑터는_도구를_받지_않는다():
    # 리포트 해석은 도구 없는 한 턴이다(v0.68.0 도구 루프 제거) — 도구가 오면 조용히 무시하지 않고 거절한다
    from apps.agent.adapter.outbound.llm.anthropic_llm_adapter import AnthropicLLMAdapter

    adapter = AnthropicLLMAdapter(model="claude-haiku-4-5", api_key="test")
    with pytest.raises(ValueError):
        adapter.chat([{"role": "user", "content": "q"}], [LLMToolSpec(name="t", description="d", input_schema={})])


def test_anthropic_키가_없으면_생성_시점에_ValueError다(monkeypatch):
    # 폴백 어댑터는 생성 실패를 "키 없음"으로 보고 다음 모델로 내려간다 — Gemini 어댑터와 같은 계약
    from apps.agent.adapter.outbound.llm import anthropic_llm_adapter

    monkeypatch.setattr(anthropic_llm_adapter, "get_settings", lambda: type("S", (), {"anthropic_api_key": ""})())
    with pytest.raises(ValueError):
        anthropic_llm_adapter.AnthropicLLMAdapter(model="claude-opus-5-5")
