from dataclasses import dataclass, field
from datetime import datetime

from apps.ops.domain.services.usage_stats import UsageSummary


@dataclass(frozen=True)
class OllamaModelDto:
    name: str
    size_bytes: int


@dataclass(frozen=True)
class OllamaStatusDto:
    reachable: bool
    base_url: str
    latency_ms: int | None = None
    models: list[OllamaModelDto] = field(default_factory=list)
    loaded: list[str] = field(default_factory=list)  # 지금 메모리에 올라온 모델
    error: str | None = None


@dataclass(frozen=True)
class RequiredModelDto:
    name: str
    purpose: str
    installed: bool
    loaded: bool


@dataclass(frozen=True)
class LlmRouteDto:
    role: str  # primary | fallback
    provider: str
    model: str
    available: bool
    detail: str


@dataclass(frozen=True)
class RecentAnalysisDto:
    id: str
    region_code: str
    industry: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    created_at: datetime


@dataclass(frozen=True)
class RagSourceStatsDto:
    source_type: str
    chunks: int
    embedded: int
    latest_published_at: datetime | None


@dataclass(frozen=True)
class EmbedderCountDto:
    model: str
    chunks: int


@dataclass(frozen=True)
class RagStatsDto:
    total_chunks: int
    embedded_chunks: int
    by_source: list[RagSourceStatsDto] = field(default_factory=list)
    embedded_by: list[EmbedderCountDto] = field(default_factory=list)


@dataclass(frozen=True)
class HealthcareSnapshotDto:
    generated_at: datetime
    llm_routes: list[LlmRouteDto]
    required_models: list[RequiredModelDto]
    ollama: OllamaStatusDto
    usage_24h: UsageSummary
    usage_7d: UsageSummary
    recent_analyses: list[RecentAnalysisDto]
    rag: RagStatsDto


@dataclass(frozen=True)
class ProbeHitDto:
    source_type: str
    source_id: str
    score: float
    snippet: str
    url: str | None


@dataclass(frozen=True)
class ProbeResultDto:
    kind: str
    ok: bool
    latency_ms: int
    model: str | None = None
    output: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    hits: list[ProbeHitDto] = field(default_factory=list)
    error: str | None = None
