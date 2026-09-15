"""RagIndexInteractor·RagSearchInteractor — Fake 포트 단위 테스트 (DB·네트워크·GPU 없음)."""

from apps.rag.app.ports.output.rag_port import EmbeddingPort, RagRepositoryPort, RagSourcePort
from apps.rag.app.use_cases.rag_interactor import RagIndexInteractor, RagSearchInteractor
from apps.rag.domain.entities.rag_chunk_entity import RagChunk, RagHit


class FakeEmbeddingPort(EmbeddingPort):
    """호출 기록용 Fake — embed_documents/embed_query 호출 인자를 보존한다."""

    def __init__(self, name: str = "fake-embedding-model") -> None:
        self._name = name
        self.embed_documents_calls: list[list[str]] = []
        self.embed_query_calls: list[str] = []

    @property
    def model_name(self) -> str:
        return self._name

    @property
    def provider(self) -> str:
        return "fake"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.embed_documents_calls.append(texts)
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        self.embed_query_calls.append(text)
        return [1.0, 0.0]


class FakeRagRepository(RagRepositoryPort):
    def __init__(self, existing_ids: set[str] | None = None) -> None:
        self.stored: dict[str, RagChunk] = {}
        self._existing_ids = existing_ids or set()
        self.search_calls: list[tuple] = []

    def upsert_chunks(self, chunks: list[RagChunk]) -> int:
        for chunk in chunks:
            self.stored[chunk.chunk_id] = chunk
        return len(chunks)

    def existing_ids(self, source_type: str) -> set[str]:
        return self._existing_ids

    def search(
        self,
        embedding: list[float],
        top_k: int,
        source_type: str | None = None,
        exclude_expired_funding: bool = True,
    ) -> list[RagHit]:
        self.search_calls.append((embedding, top_k, source_type))
        return [
            RagHit(
                chunk_id="hit1",
                source_type="funding",
                source_id="s1",
                content="검색 결과",
                score=0.9,
                url=None,
                org=None,
                published_at=None,
            )
        ]


class FakeRagSource(RagSourcePort):
    def __init__(self, chunks: list[RagChunk]) -> None:
        self._chunks = chunks

    def iter_chunks(self):
        return iter(self._chunks)


def _chunk(chunk_id: str, source_type: str = "funding") -> RagChunk:
    return RagChunk(
        chunk_id=chunk_id,
        source_type=source_type,
        source_id=chunk_id,
        content=f"content-{chunk_id}",
        published_at=None,
        org=None,
        url=None,
    )


def test_incremental_index_skips_existing_chunk_ids():
    source = FakeRagSource([_chunk("funding:1"), _chunk("funding:2")])
    repository = FakeRagRepository(existing_ids={"funding:1"})
    interactor = RagIndexInteractor(
        embedder=FakeEmbeddingPort(), repository=repository, sources=[source]
    )

    processed = interactor.index(full=False)

    assert processed == 1
    assert "funding:1" not in repository.stored
    assert "funding:2" in repository.stored


def test_full_reindex_processes_all_chunks_including_existing():
    source = FakeRagSource([_chunk("funding:1"), _chunk("funding:2")])
    repository = FakeRagRepository(existing_ids={"funding:1"})
    interactor = RagIndexInteractor(
        embedder=FakeEmbeddingPort(), repository=repository, sources=[source]
    )

    processed = interactor.index(full=True)

    assert processed == 2
    assert set(repository.stored) == {"funding:1", "funding:2"}


def test_search_embeds_query_once_and_delegates_to_repository_search():
    repository = FakeRagRepository()
    embedder = FakeEmbeddingPort()
    interactor = RagSearchInteractor(embedder=embedder, repository=repository)

    hits = interactor.search("정책자금", top_k=3, source_type="funding")

    assert embedder.embed_query_calls == ["정책자금"]
    assert repository.search_calls == [([1.0, 0.0], 3, "funding")]
    assert hits[0].chunk_id == "hit1"


def test_index_records_embedded_by_as_adapter_model_name():
    source = FakeRagSource([_chunk("funding:1")])
    repository = FakeRagRepository()
    interactor = RagIndexInteractor(
        embedder=FakeEmbeddingPort(name="test-model-x"),
        repository=repository,
        sources=[source],
    )

    interactor.index(full=False)

    assert repository.stored["funding:1"].embedded_by == "test-model-x"
