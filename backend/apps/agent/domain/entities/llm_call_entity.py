from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class LlmCallOutcome(StrEnum):
    OK = "ok"
    FALLBACK = "fallback"  # 이 시도는 실패했고 다음 모델로 넘어갔다
    ERROR = "error"  # 마지막 모델까지 실패해 호출부로 예외가 나갔다


@dataclass(frozen=True)
class LlmCall:
    """LLM 호출 시도 1회 — 성공만 남는 llm_usage와 달리 실패·폴백도 남긴다."""

    occurred_at: datetime
    model: str
    outcome: LlmCallOutcome
    latency_ms: int
    error_kind: str | None = None  # 예외 클래스 이름만 — 메시지에는 키·URL이 섞일 수 있다
