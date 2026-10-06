"""Driven Adapter — funding 원천 테이블 순회 → RagChunk 생성 (cross-BC 접근은 이 파일 안에서만).
뉴스는 색인하지 않는다 — 네이버 검색 결과는 AI 입력·평가 활용 금지(검색 API 특약 2.3)."""

from collections.abc import Iterator

from sqlalchemy import select

from apps.funding.adapter.outbound.orm_mappers.funding_program_orm_mapper import (
    to_entity as funding_to_entity,
)
from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
from apps.rag.app.ports.output.rag_port import RagSourcePort
from apps.rag.domain.entities.rag_chunk_entity import RagChunk, build_funding_chunk
from core.matrix.grid_oracle_database_manager import session_scope


class FundingRagSourceGateway(RagSourcePort):
    """funding_program 전량을 청크로 순회 — 만료 포함(만료 필터링은 검색 시점에 적용)."""

    def iter_chunks(self) -> Iterator[RagChunk]:
        with session_scope() as session:
            programs = [
                funding_to_entity(orm)
                for orm in session.execute(select(FundingProgramOrm)).scalars()
            ]
        return (build_funding_chunk(program) for program in programs)

