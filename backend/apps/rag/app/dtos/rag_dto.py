"""RAG 검색 결과 DTO — Inbound Boundary Gate(Router ↔ Interactor)에서 RagHit을 변환해 노출한다."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class RagSearchResultDto:
    chunk_id: str
    source_type: str
    source_id: str
    content: str
    score: float
    url: str | None
    org: str | None
    published_at: datetime | None
