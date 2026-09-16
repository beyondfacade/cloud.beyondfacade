"""Driven Port — Agent가 LLM 프로바이더에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMToolSpec:
    """도구 정의 — 프로바이더 중립."""

    name: str
    description: str
    input_schema: dict


@dataclass
class LLMToolCall:
    """LLM이 요청한 도구 호출."""

    tool_name: str
    arguments: dict


@dataclass
class LLMUsage:
    """토큰 사용량."""

    input_tokens: int
    output_tokens: int


@dataclass
class LLMTurn:
    """한 턴 응답: text 또는 tool_calls (둘 다 가능)."""

    text: str
    tool_calls: list[LLMToolCall]
    usage: LLMUsage


class LLMGatewayPort(ABC):
    """LLM 게이트웨이 포트 — 도구 호출이 가능한 채팅 한 턴."""

    model_name: str

    @abstractmethod
    def chat(self, messages: list[dict], tools: list[LLMToolSpec]) -> LLMTurn:
        """메시지 히스토리와 도구 목록을 받아 한 턴 응답을 반환."""
