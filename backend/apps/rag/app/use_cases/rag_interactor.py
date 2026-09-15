"""RagIndexInteractor·RagSearchInteractor — 색인/검색 오케스트레이션 (얇은 Application Service).

혼용 구도(§0 설계): 색인 임베더(fp16/ollama/gemini)와 검색 임베더(ollama)는 서로 다른
EmbeddingPort 구현을 주입받는다 — 두 UseCase가 별개 Interactor인 이유이기도 하다.
"""

from apps.rag.app.ports.input.rag_use_case import RagIndexUseCase, RagSearchUseCase
from apps.rag.app.ports.output.rag_port import EmbeddingPort, RagRepositoryPort, RagSourcePort
from apps.rag.domain.entities.rag_chunk_entity import RagHit

_EMBED_BATCH_SIZE = 32


class RagIndexInteractor(RagIndexUseCase):
    def __init__(
        self,
        embedder: EmbeddingPort,
        repository: RagRepositoryPort,
        sources: list[RagSourcePort],
    ) -> None:
        self._embedder = embedder
        self._repository = repository
        self._sources = sources

    def index(self, full: bool = False) -> int:
        processed = 0
        for source in self._sources:
            chunks = list(source.iter_chunks())
            if not chunks:
                continue
            if not full:
                existing = self._repository.existing_ids(chunks[0].source_type)
                chunks = [c for c in chunks if c.chunk_id not in existing]
            for start in range(0, len(chunks), _EMBED_BATCH_SIZE):
                batch = chunks[start : start + _EMBED_BATCH_SIZE]
                vectors = self._embedder.embed_documents([c.content for c in batch])
                for chunk, vector in zip(batch, vectors):
                    chunk.embedding = vector
                    chunk.embedded_by = self._embedder.model_name
                processed += self._repository.upsert_chunks(batch)
        return processed


class RagSearchInteractor(RagSearchUseCase):
    def __init__(self, embedder: EmbeddingPort, repository: RagRepositoryPort) -> None:
        self._embedder = embedder
        self._repository = repository

    def search(
        self, query: str, top_k: int = 5, source_type: str | None = None
    ) -> list[RagHit]:
        embedding = self._embedder.embed_query(query)
        return self._repository.search(embedding, top_k, source_type)
