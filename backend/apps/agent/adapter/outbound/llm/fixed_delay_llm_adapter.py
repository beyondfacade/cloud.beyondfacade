"""부하 테스트용 가짜 LLM 어댑터 — LLMGatewayPort 구현 (testplan §7-4 (c)).

정해진 시간만 쉬고 고정 문장을 낸다. 요금·분당 한도 없이 서버 구조(스레드 점유·DB·직렬화)의 한계만 잰다.
운영 배선에는 없다 — `LLM_MODE=fake`로 띄운 테스트 컨테이너에서만 쓴다.
"""

import time
from collections.abc import Callable, Iterator

from apps.agent.app.ports.output.agent_port import (
    LLMGatewayPort,
    LLMStreamEvent,
    LLMToolSpec,
    LLMTurn,
    LLMUsage,
)

FIXED_DELAY_SECONDS = 3.0
_FIXED_TEXT = "부하 테스트용 고정 해석입니다."


class FixedDelayLLMAdapter(LLMGatewayPort):
    model_name = "fake"

    def __init__(self, delay_seconds: float = FIXED_DELAY_SECONDS, sleep: Callable[[float], None] = time.sleep) -> None:
        self._delay_seconds = delay_seconds
        self._sleep = sleep

    def chat(self, messages: list[dict], tools: list[LLMToolSpec]) -> LLMTurn:
        self._sleep(self._delay_seconds)
        return LLMTurn(text=_FIXED_TEXT, tool_calls=[], usage=LLMUsage(input_tokens=0, output_tokens=0))

    def stream(self, messages: list[dict], tools: list[LLMToolSpec]) -> Iterator[LLMStreamEvent]:
        turn = self.chat(messages, tools)
        yield LLMStreamEvent(kind="text", text=turn.text)
        yield LLMStreamEvent(kind="tool_calls")
        yield LLMStreamEvent(kind="usage", usage=turn.usage)
