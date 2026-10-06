"""Gemini LLM 어댑터 — LLMGatewayPort 구현 (무료 티어 요청 간격 + 429 백오프)."""

import logging
import time
from collections.abc import Iterator

from google import genai
from google.genai import errors, types

from apps.agent.app.ports.output.agent_port import (
    LLMGatewayPort,
    LLMStreamEvent,
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

# 리포트 작성은 facts를 해석해 옮겨 쓰는 일이라 사전 추론이 필요 없다. 2026-09-29 실측(같은
# 시스템 프롬프트·facts): thinking ON 첫 토큰 11.7초·완료 22.5초 → OFF 첫 토큰 1.1초·완료 8.4~9.0초.
_THINKING_OFF = types.ThinkingConfig(thinking_budget=0)
# Pro는 thinking을 끌 수 없다 — budget 0을 보내면 호출이 400으로 거절된다. flash 계열에만 건다.
# gemini-3.8-flash도 budget 0을 받는다(2026-10-06 실측 1.8초 → 1.3초)
_THINKING_OFF_PREFIXES = ("gemini-2.5-flash", "gemini-3.8-flash")


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
                                "name": message.get("tool_name") or message.get("name", ""),
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


def _chunk_text(chunk) -> str:
    """조각의 본문. 함수 호출만 든 조각에서 `.text`는 경고와 함께 None이거나 예외다 — 빈 글로 본다."""
    try:
        return chunk.text or ""
    except Exception:  # SDK 버전마다 다르다. 조각 하나 때문에 스트림을 끊지 않는다
        return ""


def _usage_of(metadata, current: LLMUsage) -> LLMUsage:
    """usage_metadata는 조각마다 누적으로 실린다 — 마지막에 본 값이 그 턴의 사용량이다."""
    if metadata is None:
        return current
    return LLMUsage(
        input_tokens=metadata.prompt_token_count or 0,
        output_tokens=metadata.candidates_token_count or 0,
    )


class GeminiLLMAdapter(LLMGatewayPort):
    """Gemini generateContent 기반 LLM 어댑터."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
        temperature: float | None = None,
        seed: int | None = None,
        think: bool = False,
    ) -> None:
        """temperature·seed는 지정했을 때만 generationConfig에 싣는다(미지정이면 지금과 같은 요청).

        think=True면 flash 계열이어도 사전 추론을 끄지 않는다(모델 기본 동작) — 추론 모드 평가용.
        """
        self.model_name = model
        self._temperature = temperature
        self._seed = seed
        self._think = think
        self._client = genai.Client(api_key=api_key or get_settings().gemini_api_key)
        self._last_request_at: float | None = None

    def chat(self, messages: list[dict], tools: list[LLMToolSpec]) -> LLMTurn:
        """메시지 히스토리와 도구 목록을 받아 한 턴 응답을 반환."""
        system_instruction, contents = to_gemini_contents(messages)
        config = self._config(system_instruction, tools)

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

    def stream(self, messages: list[dict], tools: list[LLMToolSpec]) -> Iterator[LLMStreamEvent]:
        """generate_content_stream — 조각의 text는 즉시, function_calls·usage는 턴 끝에 모아 낸다."""
        system_instruction, contents = to_gemini_contents(messages)
        config = self._config(system_instruction, tools)

        tool_calls: list[LLMToolCall] = []
        usage = LLMUsage(input_tokens=0, output_tokens=0)
        for chunk in self._stream_with_retry(contents, config):
            text = _chunk_text(chunk)
            if text:
                yield LLMStreamEvent(kind="text", text=text)
            tool_calls.extend(
                LLMToolCall(tool_name=call.name, arguments=dict(call.args or {}))
                for call in (chunk.function_calls or [])
            )
            usage = _usage_of(chunk.usage_metadata, usage)
        yield LLMStreamEvent(kind="tool_calls", tool_calls=tool_calls)
        yield LLMStreamEvent(kind="usage", usage=usage)

    def _config(
        self, system_instruction: str, tools: list[LLMToolSpec]
    ) -> "types.GenerateContentConfig":
        """chat()·stream()이 함께 쓰는 호출 설정 — flash 계열이면 사전 추론을 끈다(_THINKING_OFF)."""
        return types.GenerateContentConfig(
            system_instruction=system_instruction or None,
            thinking_config=(
                _THINKING_OFF if not self._think and self.model_name.startswith(_THINKING_OFF_PREFIXES) else None
            ),
            tools=(
                [types.Tool(function_declarations=to_function_declarations(tools))]
                if tools
                else None
            ),
            temperature=self._temperature,
            seed=self._seed,
        )

    def _stream_with_retry(self, contents: list[dict], config: "types.GenerateContentConfig"):
        """429 재시도는 **첫 조각 전까지만** — 반쯤 흘려보낸 글을 처음부터 다시 쓰게 하지 않는다."""
        self._respect_min_interval()
        self._last_request_at = time.monotonic()

        waited = 0.0
        attempt = 0
        while True:
            try:
                chunks = iter(
                    self._client.models.generate_content_stream(
                        model=self.model_name, contents=contents, config=config
                    )
                )
                first = next(chunks)
            except StopIteration:  # 빈 스트림 — 계약(tool_calls·usage)은 호출부가 닫는다
                return
            except errors.ClientError as exc:
                delay = min(_RETRY_BASE_DELAY * 2**attempt, _RETRY_MAX_DELAY)
                if exc.code != 429 or waited + delay > _RETRY_BUDGET_SECONDS:
                    if exc.code == 429:
                        LOGGER.warning(
                            "LLM 스트림 429 재시도 예산 %.1fs 소진 (%d회) — 호출부가 폴백한다",
                            waited,
                            attempt + 1,
                        )
                    raise
                time.sleep(delay)
                waited += delay
                attempt += 1
                continue
            break

        yield first
        yield from chunks

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
