"""Ollama LLM 어댑터 — LLMGatewayPort 구현 (gemma3 등 로컬 모델)."""

import httpx

from apps.agent.app.ports.output.agent_port import (
    LLMGatewayPort,
    LLMToolCall,
    LLMToolSpec,
    LLMTurn,
    LLMUsage,
)


class OllamaLLMAdapter(LLMGatewayPort):
    """Ollama /api/chat 기반 LLM 어댑터."""

    def __init__(self, model: str = "gemma3:12b", base_url: str = "http://127.0.0.1:11434", transport=None):
        """
        Ollama LLM 어댑터 초기화.

        Args:
            model: Ollama 모델명 (기본값: gemma3:12b)
            base_url: Ollama 서버 URL (기본값: http://127.0.0.1:11434)
            transport: httpx.Transport (테스트용 MockTransport 주입 가능)
        """
        self.model_name = model
        self.client = httpx.Client(base_url=base_url, transport=transport, timeout=120.0)

    def chat(self, messages: list[dict], tools: list[LLMToolSpec]) -> LLMTurn:
        """메시지 히스토리와 도구 목록을 받아 한 턴 응답을 반환."""
        response = self.client.post(
            "/api/chat",
            json={
                "model": self.model_name,
                "messages": messages,
                "tools": [_to_ollama_tool(tool) for tool in tools],
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()

        message = data.get("message", {})
        tool_calls = [
            LLMToolCall(
                tool_name=call["function"]["name"],
                arguments=call["function"]["arguments"],
            )
            for call in message.get("tool_calls") or []
        ]

        return LLMTurn(
            text=message.get("content", ""),
            tool_calls=tool_calls,
            usage=LLMUsage(
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
            ),
        )


def _to_ollama_tool(tool: LLMToolSpec) -> dict:
    """LLMToolSpec → Ollama tools 항목 변환."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }
