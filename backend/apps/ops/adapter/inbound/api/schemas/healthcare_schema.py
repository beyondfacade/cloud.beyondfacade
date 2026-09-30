from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LlmRouteResponse(BaseModel):
    role: str
    provider: str
    model: str
    available: bool
    detail: str


class RequiredModelResponse(BaseModel):
    name: str
    purpose: str
    installed: bool
    loaded: bool


class OllamaModelResponse(BaseModel):
    name: str
    size_bytes: int


class OllamaStatusResponse(BaseModel):
    reachable: bool
    base_url: str
    latency_ms: int | None
    models: list[OllamaModelResponse]
    loaded: list[str]
    error: str | None


class ModelUsageResponse(BaseModel):
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    avg_latency_ms: int


class UsageSummaryResponse(BaseModel):
    window_hours: int
    calls: int
    input_tokens: int
    output_tokens: int
    p50_latency_ms: int | None
    p95_latency_ms: int | None
    by_model: list[ModelUsageResponse]


class RecentAnalysisResponse(BaseModel):
    id: str
    region_code: str
    industry: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    created_at: datetime


class RagSourceStatsResponse(BaseModel):
    source_type: str
    chunks: int
    embedded: int
    latest_published_at: datetime | None


class EmbedderCountResponse(BaseModel):
    model: str
    chunks: int


class RagStatsResponse(BaseModel):
    total_chunks: int
    embedded_chunks: int
    by_source: list[RagSourceStatsResponse]
    embedded_by: list[EmbedderCountResponse]


class HealthcareSnapshotResponse(BaseModel):
    generated_at: datetime
    llm_routes: list[LlmRouteResponse]
    required_models: list[RequiredModelResponse]
    ollama: OllamaStatusResponse
    usage_24h: UsageSummaryResponse
    usage_7d: UsageSummaryResponse
    recent_analyses: list[RecentAnalysisResponse]
    rag: RagStatsResponse


class ProbeRequest(BaseModel):
    kind: Literal["rag", "llm"]
    message: str = Field(min_length=1, max_length=500)


class ProbeHitResponse(BaseModel):
    source_type: str
    source_id: str
    score: float
    snippet: str
    url: str | None


class ProbeResultResponse(BaseModel):
    kind: str
    ok: bool
    latency_ms: int
    model: str | None
    output: str | None
    input_tokens: int | None
    output_tokens: int | None
    hits: list[ProbeHitResponse]
    error: str | None
