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


class FakeDuplicateNewsRepository(FakeRagRepository):
    """같은 사건 기사 3건 + 다른 사건 1건을 점수순으로 돌려준다 — top_k보다 많이 요청받아야 접을 수 있다."""

    def search(self, embedding, top_k, source_type=None, exclude_expired_funding=True):
        self.search_calls.append((embedding, top_k, source_type))
        from datetime import datetime

        def hit(cid, title, score):
            return RagHit(chunk_id=cid, source_type="news", source_id=cid, content=f"{title}\n요약",
                          score=score, url=None, org=None, published_at=datetime(2026, 9, 21))
        return [
            hit("n1", "코웨이, 롯데백화점 노원점에 올해 10번째 직영매장 개점", 0.9),
            hit("n2", "코웨이, 노원 롯데백화점에 올해 10번째 직영매장", 0.85),
            hit("n3", "코웨이, 롯데百 노원점에 10번째 공식 직영매장", 0.8),
            hit("n4", "홈앤쇼핑, 둔촌역전통시장서 디지털 전환 지원", 0.7),
        ][:top_k]


def test_search_news는_같은_사건을_접어_서로_다른_사건으로_top_k를_채운다():
    repository = FakeDuplicateNewsRepository()
    interactor = RagSearchInteractor(embedder=FakeEmbeddingPort(), repository=repository)

    hits = interactor.search("코웨이 노원 매장", top_k=2, source_type="news")

    assert [h.chunk_id for h in hits] == ["n1", "n4"]
    assert repository.search_calls[0][1] > 2  # 접을 여유분을 더 가져온다


def test_search_funding은_접지_않고_top_k_그대로_요청한다():
    repository = FakeRagRepository()
    interactor = RagSearchInteractor(embedder=FakeEmbeddingPort(), repository=repository)

    interactor.search("소상공인 대출", top_k=5, source_type="funding")

    assert repository.search_calls[0][1] == 5
