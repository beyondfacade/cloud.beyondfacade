"""Gemini LLM 어댑터 — LLMGatewayPort 구현 (무료 티어 요청 간격 + 429 백오프)."""

import logging
import time

from google import genai
from google.genai import errors, types

from apps.agent.app.ports.output.agent_port import (
    LLMGatewayPort,
    LLMToolCall,
    LLMToolSpec,
    LLMTurn,
    LLMUsage,
)
from core.matrix.grid_keymaker_secret_manager import get_settings

LOGGER = logging.getLogger("beyondfacade.agent.llm")

# 무료 티어 분당 요청 제한 대비 — 요청 간 최소 간격
_MIN_REQUEST_INTERVAL_SECONDS = 4.0

# 429 재시도 관행은 gemini_embedding_adapter.py와 동일
_RETRY_BASE_DELAY = 0.5
_RETRY_MAX_DELAY = 4.0
_RETRY_BUDGET_SECONDS = 30.0


def to_gemini_contents(messages: list[dict]) -> tuple[str, list[dict]]:
    """Ollama chat 포맷 메시지 → Gemini (system_instruction, contents) 변환.

    role 매핑: system → system_instruction으로 분리 수집, user → user,
    assistant → model (tool_calls 있으면 functionCall 파트), tool → 결과를
    functionResponse 파트로 감싼 user 턴 (Gemini는 user/model 두 role만 허용).
    """
    system_parts: list[str] = []
    contents: list[dict] = []

    for message in messages:
        role = message["role"]
        if role == "system":
            system_parts.append(message["content"])
        elif role == "user":
            contents.append({"role": "user", "parts": [{"text": message["content"]}]})
        elif role == "assistant":
            tool_calls = message.get("tool_calls")
            if tool_calls:
                parts = [
                    {
                        "functionCall": {
                            "name": call["function"]["name"],
                            "args": call["function"]["arguments"],
                        }
                    }
                    for call in tool_calls
                ]
            else:
                parts = [{"text": message["content"]}]
            contents.append({"role": "model", "parts": parts})
        elif role == "tool":
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": message.get("name", ""),
                                "response": {"result": message["content"]},
                            }
                        }
                    ],
                }
            )

    return "\n".join(system_parts), contents


def to_function_declarations(tools: list[LLMToolSpec]) -> list[dict]:
    """LLMToolSpec 목록 → Gemini function_declarations."""
    return [
        {"name": tool.name, "description": tool.description, "parameters": tool.input_schema}
        for tool in tools
    ]


class GeminiLLMAdapter(LLMGatewayPort):
    """Gemini generateContent 기반 LLM 어댑터."""

    def __init__(self, model: str = "gemini-2.0-flash", api_key: str | None = None) -> None:
        self.model_name = model
        self._client = genai.Client(api_key=api_key or get_settings().gemini_api_key)
        self._last_request_at: float | None = None

    def chat(self, messages: list[dict], tools: list[LLMToolSpec]) -> LLMTurn:
        """메시지 히스토리와 도구 목록을 받아 한 턴 응답을 반환."""
        system_instruction, contents = to_gemini_contents(messages)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            tools=(
                [types.Tool(function_declarations=to_function_declarations(tools))]
                if tools
                else None
            ),
        )

        response = self._generate_with_retry(contents, config)

        tool_calls = [
            LLMToolCall(tool_name=call.name, arguments=dict(call.args or {}))
            for call in (response.function_calls or [])
        ]
        usage = response.usage_metadata
        return LLMTurn(
            text=response.text or "",
            tool_calls=tool_calls,
            usage=LLMUsage(
                input_tokens=(usage.prompt_token_count or 0) if usage else 0,
                output_tokens=(usage.candidates_token_count or 0) if usage else 0,
            ),
        )

    def _generate_with_retry(self, contents: list[dict], config: "types.GenerateContentConfig"):
        self._respect_min_interval()
        self._last_request_at = time.monotonic()

        # 전역 공용 쿼터(429) 대비 — 지수 백오프로 예산 안에서 재시도
        waited = 0.0
        attempt = 0
        while True:
            try:
                return self._client.models.generate_content(
                    model=self.model_name, contents=contents, config=config
                )
            except errors.ClientError as exc:
                delay = min(_RETRY_BASE_DELAY * 2**attempt, _RETRY_MAX_DELAY)
                if exc.code != 429 or waited + delay > _RETRY_BUDGET_SECONDS:
                    if exc.code == 429:
                        LOGGER.warning(
                            "LLM 호출 429 재시도 예산 %.1fs 소진 (%d회) — 호출부가 폴백한다",
                            waited,
                            attempt + 1,
                        )
                    raise
                time.sleep(delay)
                waited += delay
                attempt += 1

    def _respect_min_interval(self) -> None:
        """요청 간 최소 간격(무료 티어)을 지키기 위해 남은 시간만큼 대기."""
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = _MIN_REQUEST_INTERVAL_SECONDS - elapsed
        if remaining > 0:
            time.sleep(remaining)
