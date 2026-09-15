"""Driven Adapter — funding/news 원천 테이블 순회 → RagChunk 생성 (cross-BC 접근은 이 파일 안에서만)."""

from collections.abc import Iterator

from sqlalchemy import select

from apps.funding.adapter.outbound.orm_mappers.funding_program_orm_mapper import (
    to_entity as funding_to_entity,
)
from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
from apps.news.adapter.outbound.orm_mappers.news_article_orm_mapper import (
    to_entity as news_to_entity,
)
from apps.news.adapter.outbound.orms.news_article_orm import NewsArticleOrm
from apps.rag.app.ports.output.rag_port import RagSourcePort
from apps.rag.domain.entities.rag_chunk_entity import RagChunk, build_funding_chunk, build_news_chunk
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


class NewsRagSourceGateway(RagSourcePort):
    """news_article 전량을 청크로 순회."""

    def iter_chunks(self) -> Iterator[RagChunk]:
        with session_scope() as session:
            articles = [
                news_to_entity(orm)
                for orm in session.execute(select(NewsArticleOrm)).scalars()
            ]
        return (build_news_chunk(article) for article in articles)
