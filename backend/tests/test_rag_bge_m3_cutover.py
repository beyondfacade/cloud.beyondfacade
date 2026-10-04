"""운영 임베딩 bge-m3@1024 전환 — 레지스트리·ORM 차원 계약."""
from apps.rag.adapter.outbound.embeddings.ollama_bge_m3_adapter import OllamaBgeM3EmbeddingAdapter
from apps.rag.adapter.outbound.orms.rag_chunk_orm import RagChunkOrm
from apps.rag.dependencies.rag_dependencies import (
    INDEX_PROVIDERS,
    get_rag_index_use_case,
    get_rag_search_use_case,
)


def test_검색_UseCase_기본_임베더는_bge_m3다():
    embedder = get_rag_search_use_case()._embedder
    assert isinstance(embedder, OllamaBgeM3EmbeddingAdapter)
    assert embedder.model_name == "bge-m3"


def test_색인_UseCase_기본_임베더는_bge_m3다():
    embedder = get_rag_index_use_case()._embedder
    assert isinstance(embedder, OllamaBgeM3EmbeddingAdapter)
    assert embedder.model_name == "bge-m3"


def test_운영_레지스트리는_bge_m3_하나뿐이다():
    assert INDEX_PROVIDERS == ("bge-m3",)


def test_rag_chunk_embedding_컬럼은_1024차원이다():
    assert RagChunkOrm.__table__.c.embedding.type.dim == 1024
