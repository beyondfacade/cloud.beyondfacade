"""OllamaLLMAdapter·GeminiLLMAdapter 검증 — httpx.MockTransport 및 변환 함수 단위 테스트."""

import json

import httpx

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
    """메시지 role 매핑: system→system_instruction 분리, user→user, assistant→model."""
    from apps.agent.adapter.outbound.llm.gemini_llm_adapter import to_gemini_contents

    messages = [
        {"role": "system", "content": "너는 상점 안내 봇이다."},
        {"role": "user", "content": "카페 추천해줘"},
        {"role": "assistant", "content": "네, 찾아볼게요"},
    ]

    system_instruction, contents = to_gemini_contents(messages)

    assert system_instruction == "너는 상점 안내 봇이다."
    assert contents[0]["role"] == "user"
    assert contents[0]["parts"][0]["text"] == "카페 추천해줘"
    assert contents[1]["role"] == "model"
    assert contents[1]["parts"][0]["text"] == "네, 찾아볼게요"


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
