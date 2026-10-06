"""Anthropic(Claude) LLM 어댑터 — LLMGatewayPort 구현. 리포트 해석 한 턴(도구 없음)만 지원한다.
운영 1차 해석 모델(claude-opus-5-5, 2026-10-06 평가 — data/eval/results/claude-models-2026-10-06/notes.md).

모델별 요청 차이(2026-10 기준): Claude Opus 5.5·Sonnet 5.5는 temperature를 받지 않는다(400) — 온도는 Haiku 4.5에만 싣는다.
Opus 5.5는 생각을 끌 수 없어 effort로만 줄이고, Sonnet 5.5는 `between_tools`로 끈다(도구가 없으니 생각 없이 답한다).
"""

from collections.abc import Iterator

import anthropic

from apps.agent.app.ports.output.agent_port import (
    LLMGatewayPort,
    LLMStreamEvent,
    LLMToolSpec,
    LLMTurn,
    LLMUsage,
)
from core.matrix.grid_keymaker_secret_manager import get_settings

_MAX_TOKENS = 16000


def to_anthropic_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """Ollama chat 포맷 → (system, messages). system은 top-level로 모으고 user·assistant만 남긴다."""
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] in ("user", "assistant")]
    return system, rest


class AnthropicLLMAdapter(LLMGatewayPort):
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        temperature: float | None = None,
        thinking: dict | None = None,
        effort: str | None = None,
    ) -> None:
        """temperature·thinking·effort는 지정했을 때만 요청에 싣는다 — 모델마다 받는 값이 달라 호출부(배선)가 정한다."""
        self.model_name = model
        self._options: dict = {}
        if temperature is not None:
            # SDK 1.x 시그니처에서 빠졌다 — 받는 모델(Haiku 4.5)에만 extra_body로 싣는다
            self._options["extra_body"] = {"temperature": temperature}
        if thinking is not None:
            self._options["thinking"] = thinking
        if effort is not None:
            self._options["output_config"] = {"effort": effort}
        key = api_key or get_settings().anthropic_api_key
        if not key:  # 생성 시점 실패 = 키 없음 — 폴백 어댑터가 다음 모델로 내려간다(Gemini 어댑터와 같은 계약)
            raise ValueError("ANTHROPIC_API_KEY가 없다")
        self._client = anthropic.Anthropic(api_key=key)

    def chat(self, messages: list[dict], tools: list[LLMToolSpec]) -> LLMTurn:
        response = self._client.messages.create(**self._request(messages, tools))
        # refusal이면 본문이 비어 온다 — 빈 해석은 호출부 가드가 폴백으로 넘긴다
        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMTurn(
            text=text,
            tool_calls=[],
            usage=LLMUsage(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens),
        )

    def stream(self, messages: list[dict], tools: list[LLMToolSpec]) -> Iterator[LLMStreamEvent]:
        with self._client.messages.stream(**self._request(messages, tools)) as stream:
            for text in stream.text_stream:
                yield LLMStreamEvent(kind="text", text=text)
            usage = stream.get_final_message().usage
        yield LLMStreamEvent(kind="tool_calls", tool_calls=[])
        yield LLMStreamEvent(kind="usage", usage=LLMUsage(input_tokens=usage.input_tokens, output_tokens=usage.output_tokens))

    def _request(self, messages: list[dict], tools: list[LLMToolSpec]) -> dict:
        if tools:
            raise ValueError("AnthropicLLMAdapter는 도구 호출을 지원하지 않는다 — 리포트 해석은 도구 없는 한 턴이다")
        system, rest = to_anthropic_messages(messages)
        request = {"model": self.model_name, "max_tokens": _MAX_TOKENS, "messages": rest, **self._options}
        return {**request, "system": system} if system else request  # 빈 system은 보내지 않는다
