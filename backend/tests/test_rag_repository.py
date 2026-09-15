"""SqlAlchemyRagRepository — 업서트 + 코사인 검색 + 만료 공고 필터 (실 DB)."""

from datetime import date, datetime

from sqlalchemy import delete

from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
from apps.rag.adapter.outbound.orms.rag_chunk_orm import RagChunkOrm
from apps.rag.adapter.outbound.repositories.rag_repository import SqlAlchemyRagRepository
from apps.rag.domain.entities.rag_chunk_entity import RagChunk
from core.matrix.grid_oracle_database_manager import session_scope

_PREFIX = "test:"
_FUNDING_PREFIX = "test-rag-repo-"

# 결정적 축 벡터 — e0·e1은 직교(orthogonal), 코사인 거리 1(score 0.0); 자기 자신은 거리 0(score 1.0)
_E0 = [1.0] + [0.0] * 1535
_E1 = [0.0, 1.0] + [0.0] * 1534


def _chunk(chunk_id: str, source_type: str, source_id: str, embedding: list[float]) -> RagChunk:
    return RagChunk(
        chunk_id=f"{_PREFIX}{chunk_id}",
        source_type=source_type,
        source_id=source_id,
        content=f"content-{chunk_id}",
        published_at=None,
        org=None,
        url=None,
        embedding=embedding,
    )


def _cleanup():
    with session_scope() as session:
        session.execute(delete(RagChunkOrm).where(RagChunkOrm.chunk_id.like(f"{_PREFIX}%")))
        session.execute(
            delete(FundingProgramOrm).where(FundingProgramOrm.program_id.like(f"{_FUNDING_PREFIX}%"))
        )


def test_search_orders_by_cosine_similarity_and_scores_self_match_near_one():
    """source_type을 실데이터가 절대 쓰지 않는 전용 값으로 격리 — Task 6 이후 rag_chunk에
    실 청크 수천 건이 쌓여도 이 두 축 벡터만 검색되도록 해 순위 침범에 흔들리지 않게 한다."""
    _cleanup()
    repo = SqlAlchemyRagRepository()
    try:
        repo.upsert_chunks(
            [
                _chunk("e0", "test_axis", "s0", _E0),
                _chunk("e1", "test_axis", "s1", _E1),
            ]
        )

        hits = repo.search(embedding=_E0, top_k=2, source_type="test_axis")
        ours = [h for h in hits if h.chunk_id.startswith(_PREFIX)]

        assert ours[0].chunk_id == f"{_PREFIX}e0"
        assert ours[0].score > 0.999
        assert ours[1].chunk_id == f"{_PREFIX}e1"
        assert ours[1].score < ours[0].score
        assert ours[1].score == 0.0
    finally:
        _cleanup()


def test_search_default_filter_does_not_drop_non_funding_chunks():
    """exclude_expired_funding=True(기본값)이어도 non-funding 청크는 살아남아야 한다 — NULL join 드롭 방지."""
    _cleanup()
    repo = SqlAlchemyRagRepository()
    try:
        repo.upsert_chunks([_chunk("news1", "news", "n1", _E0)])

        hits = repo.search(embedding=_E0, top_k=5, exclude_expired_funding=True)
        ids = {h.chunk_id for h in hits}

        assert f"{_PREFIX}news1" in ids
    finally:
        _cleanup()


def test_search_source_type_filter():
    _cleanup()
    repo = SqlAlchemyRagRepository()
    try:
        repo.upsert_chunks(
            [
                _chunk("news2", "news", "n2", _E0),
                _chunk("academy1", "academy", "a1", _E0),
            ]
        )

        hits = repo.search(embedding=_E0, top_k=10, source_type="academy")
        ids = {h.chunk_id for h in hits}

        assert f"{_PREFIX}academy1" in ids
        assert f"{_PREFIX}news2" not in ids
    finally:
        _cleanup()


def test_search_excludes_expired_funding_chunk_by_default():
    _cleanup()
    repo = SqlAlchemyRagRepository()
    try:
        with session_scope() as session:
            session.add(
                FundingProgramOrm(
                    program_id=f"{_FUNDING_PREFIX}expired1",
                    source="bizinfo",
                    title="만료 공고",
                    org="기관",
                    url=f"https://example.com/{_FUNDING_PREFIX}expired1",
                    apply_period="",
                    is_expired=True,
                )
            )
        repo.upsert_chunks(
            [_chunk("funding-expired", "funding", f"{_FUNDING_PREFIX}expired1", _E0)]
        )

        excluded = repo.search(embedding=_E0, top_k=10, exclude_expired_funding=True)
        included = repo.search(embedding=_E0, top_k=10, exclude_expired_funding=False)

        assert f"{_PREFIX}funding-expired" not in {h.chunk_id for h in excluded}
        assert f"{_PREFIX}funding-expired" in {h.chunk_id for h in included}
    finally:
        _cleanup()


def test_existing_ids_returns_chunk_ids_for_source_type():
    _cleanup()
    repo = SqlAlchemyRagRepository()
    try:
        repo.upsert_chunks(
            [
                _chunk("news3", "news", "n3", _E0),
                _chunk("academy2", "academy", "a2", _E0),
            ]
        )

        ids = repo.existing_ids("news")

        assert f"{_PREFIX}news3" in ids
        assert f"{_PREFIX}academy2" not in ids
    finally:
        _cleanup()


def test_upsert_chunks_updates_existing_row_on_second_call():
    _cleanup()
    repo = SqlAlchemyRagRepository()
    try:
        count1 = repo.upsert_chunks([_chunk("upsert1", "news", "u1", _E0)])
        assert count1 == 1

        updated = _chunk("upsert1", "news", "u1", _E1)
        updated.content = "changed"
        count2 = repo.upsert_chunks([updated])
        assert count2 == 1

        with session_scope() as session:
            row = session.get(RagChunkOrm, f"{_PREFIX}upsert1")
            assert row.content == "changed"
    finally:
        _cleanup()
