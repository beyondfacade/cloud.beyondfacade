"""RagChunk/RagHit 엔티티 + 원천 → 청크 순수 빌더 (프레임워크·타 BC 런타임 import 금지)."""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 타입 힌트 전용 — 런타임에는 import되지 않는다 (domain은 타 BC를 참조하지 않는다).
    from apps.funding.domain.entities.funding_program_entity import FundingProgram


@dataclass
class RagChunk:
    """RAG 인덱싱 단위 — 원천(funding/news 등)에서 추출한 텍스트 + 메타데이터."""

    chunk_id: str
    source_type: str
    source_id: str
    content: str
    published_at: datetime | None
    org: str | None
    url: str | None
    region_code: str | None = None
    embedding: list[float] | None = None
    embedded_by: str | None = None


@dataclass
class RagHit:
    """벡터 유사도 검색 결과 1건."""

    chunk_id: str
    source_type: str
    source_id: str
    content: str
    score: float
    url: str | None
    org: str | None
    published_at: datetime | None


def build_funding_chunk(program: "FundingProgram") -> RagChunk:
    """정책자금 공고 → RagChunk. title/org/field_category/target_text/hashtags/summary 연결.

    선택 필드(None)는 빈 문자열로 취급 — 콘텐츠에 "None" 문자열이 섞이지 않도록 한다.
    """
    parts = [
        program.title,
        program.org,
        program.field_category or "",
        program.target_text or "",
        program.hashtags or "",
        program.summary or "",
    ]
    content = "\n".join(part for part in parts if part)
    return RagChunk(
        chunk_id=f"funding:{program.program_id}",
        source_type="funding",
        source_id=program.program_id,
        content=content,
        published_at=program.posted_at,
        org=program.org,
        url=program.url,
    )


def build_news_chunk(article) -> RagChunk:
    """뉴스 기사 → RagChunk. content = title + 개행 + description만 사용 (본문 미저장 — 저작권 경계)."""
    title = article.title or ""
    description = article.description or ""
    return RagChunk(
        chunk_id=f"news:{article.article_id}",
        source_type="news",
        source_id=article.article_id,
        content=f"{title}\n{description}",
        published_at=article.published_at,
        org=article.press,
        url=article.url,
    )
