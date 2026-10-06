"""Composition Root (DIP) — RAG 색인·검색 UseCase 배선.

색인·검색 모두 bge-m3(Ollama, 1024차원, 프리픽스 없음) — 같은 모델이라 혼용 구도가 없다.
근거: data/eval/results/embedding-benchmark-2026-10-04/report.md (qwen3와 MRR 동률,
GPU 메모리 664MB vs 4.4GB). provider는 Factory Method 레지스트리(CLAUDE.md §5)로 선택한다.
qwen3·gemini 어댑터는 1536차원 출력이라 rag_chunk(vector(1024))에 넣을 수 없어 운영 레지스트리에서
뺐다(벤치마크 benchmark_embeddings.py가 직접 쓴다).
"""

from apps.rag.adapter.outbound.embeddings.ollama_bge_m3_adapter import (
    OllamaBgeM3EmbeddingAdapter,
)
from apps.rag.adapter.outbound.gateways.rag_source_gateway import FundingRagSourceGateway
from apps.rag.adapter.outbound.repositories.rag_repository import SqlAlchemyRagRepository
from apps.rag.app.ports.input.rag_use_case import RagIndexUseCase, RagSearchUseCase
from apps.rag.app.use_cases.rag_interactor import RagIndexInteractor, RagSearchInteractor

# 임베더 레지스트리 — provider 문자열 → 어댑터 클래스 (if/elif 대신 dict 디스패치)
_INDEX_EMBEDDER_REGISTRY = {
    "bge-m3": OllamaBgeM3EmbeddingAdapter,
}
# CLI --provider choices의 단일 원천
INDEX_PROVIDERS = tuple(_INDEX_EMBEDDER_REGISTRY)


def get_rag_search_use_case(provider: str = "bge-m3") -> RagSearchUseCase:
    """검색 UseCase. 임베더는 색인과 같은 모델이어야 한다 — 레지스트리 재사용(어댑터 구성 중복 금지)."""
    embedder_cls = _INDEX_EMBEDDER_REGISTRY[provider]
    return RagSearchInteractor(
        embedder=embedder_cls(),
        repository=SqlAlchemyRagRepository(),
    )


def get_rag_index_use_case(provider: str = "bge-m3") -> RagIndexUseCase:
    embedder_cls = _INDEX_EMBEDDER_REGISTRY[provider]
    return RagIndexInteractor(
        embedder=embedder_cls(),
        repository=SqlAlchemyRagRepository(),
        sources=[FundingRagSourceGateway()],  # 뉴스는 색인하지 않는다(네이버 검색 API 특약 2.3)
    )
