"""Composition Root (DIP) — RAG 색인·검색 UseCase 배선.

혼용 구도(§0 설계): 검색 임베더는 항상 Ollama Q4(저지연·상시 가용) 고정. 색인 임베더는
provider로 선택 — Factory Method 레지스트리(CLAUDE.md §5)로 if/elif 분기를 피한다.
"""

from apps.rag.adapter.outbound.embeddings.fp16_qwen3_adapter import Fp16Qwen3EmbeddingAdapter
from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import (
    GeminiEmbeddingAdapter,
)
from apps.rag.adapter.outbound.embeddings.ollama_qwen3_adapter import (
    OllamaQwen3EmbeddingAdapter,
)
from apps.rag.adapter.outbound.gateways.rag_source_gateway import (
    FundingRagSourceGateway,
    NewsRagSourceGateway,
)
from apps.rag.adapter.outbound.repositories.rag_repository import SqlAlchemyRagRepository
from apps.rag.app.ports.input.rag_use_case import RagIndexUseCase, RagSearchUseCase
from apps.rag.app.use_cases.rag_interactor import RagIndexInteractor, RagSearchInteractor

# 색인 임베더 레지스트리 — provider 문자열 → 어댑터 클래스 (if/elif 대신 dict 디스패치)
_INDEX_EMBEDDER_REGISTRY = {
    "fp16": Fp16Qwen3EmbeddingAdapter,
    "ollama": OllamaQwen3EmbeddingAdapter,
    "gemini": GeminiEmbeddingAdapter,
}


def get_rag_search_use_case(provider: str = "ollama") -> RagSearchUseCase:
    """검색 UseCase. 운영 기본값은 항상 ollama(§0 혼용 구도) — provider는 평가 하네스가

    query 임베더를 fp16/gemini로 스왑해 비교 평가할 때만 넘긴다(레지스트리 재사용, 어댑터
    구성 중복 금지).
    """
    embedder_cls = _INDEX_EMBEDDER_REGISTRY[provider]
    return RagSearchInteractor(
        embedder=embedder_cls(),
        repository=SqlAlchemyRagRepository(),
    )


def get_rag_index_use_case(provider: str = "fp16") -> RagIndexUseCase:
    embedder_cls = _INDEX_EMBEDDER_REGISTRY[provider]
    return RagIndexInteractor(
        embedder=embedder_cls(),
        repository=SqlAlchemyRagRepository(),
        sources=[FundingRagSourceGateway(), NewsRagSourceGateway()],
    )
