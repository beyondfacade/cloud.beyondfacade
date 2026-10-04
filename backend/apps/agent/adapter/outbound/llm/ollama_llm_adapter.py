"""Ollama LLM 어댑터 — LLMGatewayPort 구현 (gemma3 등 로컬 모델)."""

import json
from collections.abc import Iterator

import httpx

from apps.agent.app.ports.output.agent_port import (
    LLMGatewayPort,
    LLMStreamEvent,
    LLMToolCall,
    LLMToolSpec,
    LLMTurn,
    LLMUsage,
)
from core.matrix.grid_keymaker_secret_manager import get_settings


class OllamaLLMAdapter(LLMGatewayPort):
    """Ollama /api/chat 기반 LLM 어댑터."""

    def __init__(
        self,
        model: str = "gemma3:12b",
        base_url: str | None = None,
        transport=None,
        think: bool | None = None,
        temperature: float | None = None,
        num_ctx: int | None = None,
    ):
        """
        Ollama LLM 어댑터 초기화.

        Args:
            model: Ollama 모델명 (기본값: gemma3:12b)
            base_url: Ollama 서버 URL (기본값: 설정 OLLAMA_BASE_URL)
            transport: httpx.Transport (테스트용 MockTransport 주입 가능)
            think: 추론(thinking) 사용 여부 (기본값: None — 요청에 싣지 않음)
            temperature: 샘플링 온도 (기본값: None — 요청에 싣지 않음)
            num_ctx: 컨텍스트 길이 (기본값: None — 요청에 싣지 않음, Ollama 기본값 사용)
        """
        self.model_name = model
        self._think = think
        self._temperature = temperature
        self._num_ctx = num_ctx
        self.client = httpx.Client(base_url=base_url or get_settings().ollama_base_url, transport=transport, timeout=120.0)

    def _body(self, messages: list[dict], tools: list[LLMToolSpec], stream: bool) -> dict:
        """요청 바디 — think·temperature는 지정했을 때만 싣는다(미지정이면 지금과 같은 요청)."""
        body = {
            "model": self.model_name,
            "messages": messages,
            "tools": [_to_ollama_tool(tool) for tool in tools],
            "stream": stream,
        }
        if self._think is not None:
            body["think"] = self._think
        options = {
            key: value
            for key, value in (("temperature", self._temperature), ("num_ctx", self._num_ctx))
            if value is not None
        }
        if options:
            body["options"] = options
        return body

    def chat(self, messages: list[dict], tools: list[LLMToolSpec]) -> LLMTurn:
        """메시지 히스토리와 도구 목록을 받아 한 턴 응답을 반환."""
        response = self.client.post(
            "/api/chat",
            json=self._body(messages, tools, stream=False),
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

    def stream(self, messages: list[dict], tools: list[LLMToolSpec]) -> Iterator[LLMStreamEvent]:
        """`stream: true` NDJSON — 줄마다 message.content 조각, 도구 호출은 마지막 메시지에 온다."""
        tool_calls: list[LLMToolCall] = []
        usage = LLMUsage(input_tokens=0, output_tokens=0)
        with self.client.stream(
            "POST",
            "/api/chat",
            json=self._body(messages, tools, stream=True),
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.strip():
                    continue
                data = json.loads(line)
                message = data.get("message") or {}
                text = message.get("content") or ""
                if text:
                    yield LLMStreamEvent(kind="text", text=text)
                tool_calls.extend(_to_tool_calls(message))
                usage = _usage_of(data, usage)
        yield LLMStreamEvent(kind="tool_calls", tool_calls=tool_calls)
        yield LLMStreamEvent(kind="usage", usage=usage)


def _to_tool_calls(message: dict) -> list[LLMToolCall]:
    return [
        LLMToolCall(tool_name=call["function"]["name"], arguments=call["function"]["arguments"])
        for call in message.get("tool_calls") or []
    ]


def _usage_of(data: dict, current: LLMUsage) -> LLMUsage:
    """토큰 수는 마지막(done) 줄에만 실린다 — 값이 없는 줄은 앞서 본 값을 유지한다."""
    if "prompt_eval_count" not in data and "eval_count" not in data:
        return current
    return LLMUsage(
        input_tokens=data.get("prompt_eval_count") or 0,
        output_tokens=data.get("eval_count") or 0,
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
