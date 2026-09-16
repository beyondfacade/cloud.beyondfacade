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


class RegionFactsPort(ABC):
    """Driven Port — Agent 도구가 필요로 하는 타 BC 사실 조회 (cross-BC 접근은 구현체 안에서만)."""

    @abstractmethod
    def metrics(self, region_code: str, industry: str) -> list[dict]:
        """행정동×업종의 연도별 지표(점포수·폐업률·성장률)."""

    @abstractmethod
    def summary(self, region_code: str, industry_id: str) -> dict:
        """사이드패널 카드와 동일한 마스터 요약(fact 카드 목록)."""

    @abstractmethod
    def population(self, region_code: str) -> dict:
        """최신 기간의 연령 분포 + 학령(5~19세) 인구 합계."""

    @abstractmethod
    def shocks(self, industry_id: str | None, limit: int) -> list[dict]:
        """업종 필터(선택) 충격 이벤트 목록."""

    @abstractmethod
    def latest_rates(self) -> dict:
        """금리 유형별 최신값 (키에 loan_facility 포함)."""
