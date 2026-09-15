"""RAG 청크 저장소 — 업서트(merge) + pgvector 코사인 유사도 검색.

만료 공고 필터(exclude_expired_funding)를 위해 apps.funding의 FundingProgramOrm을 참조한다.
BC 경계를 넘는 이 import는 플랜 승인 사항이며, 이 파일 안에만 국한한다.
"""

from sqlalchemy import or_, select

from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
from apps.rag.adapter.outbound.orm_mappers.rag_chunk_orm_mapper import to_orm
from apps.rag.adapter.outbound.orms.rag_chunk_orm import RagChunkOrm
from apps.rag.app.ports.output.rag_port import RagRepositoryPort
from apps.rag.domain.entities.rag_chunk_entity import RagChunk, RagHit
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyRagRepository(RagRepositoryPort):
    def upsert_chunks(self, chunks: list[RagChunk]) -> int:
        if not chunks:
            return 0
        deduped = {c.chunk_id: c for c in chunks}  # 배치 내 동일 chunk_id는 마지막 것만
        with session_scope() as session:
            for chunk in deduped.values():
                session.merge(to_orm(chunk))
        return len(deduped)

    def existing_ids(self, source_type: str) -> set[str]:
        with session_scope() as session:
            rows = session.execute(
                select(RagChunkOrm.chunk_id).where(RagChunkOrm.source_type == source_type)
            ).scalars()
            return set(rows)

    def search(
        self,
        embedding: list[float],
        top_k: int,
        source_type: str | None = None,
        exclude_expired_funding: bool = True,
    ) -> list[RagHit]:
        distance = RagChunkOrm.embedding.cosine_distance(embedding)
        score = (1 - distance).label("score")
        stmt = select(RagChunkOrm, score).where(RagChunkOrm.embedding.is_not(None))

        if exclude_expired_funding:
            # outerjoin은 funding 청크에만 매칭되도록 조인 조건에 source_type을 넣는다.
            # non-funding 행은 조인 결과가 NULL이 되므로, where도 "funding이 아니면 무조건 통과"로
            # 구성해야 NULL join으로 non-funding 청크가 통째로 드롭되는 사고를 막는다.
            stmt = stmt.outerjoin(
                FundingProgramOrm,
                (RagChunkOrm.source_type == "funding")
                & (RagChunkOrm.source_id == FundingProgramOrm.program_id),
            ).where(
                or_(
                    RagChunkOrm.source_type != "funding",
                    FundingProgramOrm.is_expired.is_(False),
                )
            )

        if source_type is not None:
            stmt = stmt.where(RagChunkOrm.source_type == source_type)

        stmt = stmt.order_by(distance).limit(top_k)

        with session_scope() as session:
            rows = session.execute(stmt).all()
            return [
                RagHit(
                    chunk_id=orm.chunk_id,
                    source_type=orm.source_type,
                    source_id=orm.source_id,
                    content=orm.content,
                    score=float(row_score),
                    url=orm.url,
                    org=orm.org,
                    published_at=orm.published_at,
                )
                for orm, row_score in rows
            ]
