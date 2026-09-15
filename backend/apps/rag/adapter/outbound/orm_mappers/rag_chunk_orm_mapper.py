"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.rag.adapter.outbound.orms.rag_chunk_orm import RagChunkOrm
from apps.rag.domain.entities.rag_chunk_entity import RagChunk

_FIELDS = (
    "chunk_id",
    "source_type",
    "source_id",
    "content",
    "embedding",
    "embedded_by",
    "published_at",
    "org",
    "url",
    "region_code",
)


def to_orm(entity: RagChunk) -> RagChunkOrm:
    return RagChunkOrm(**{name: getattr(entity, name) for name in _FIELDS})


def to_entity(orm: RagChunkOrm) -> RagChunk:
    return RagChunk(**{name: getattr(orm, name) for name in _FIELDS})
