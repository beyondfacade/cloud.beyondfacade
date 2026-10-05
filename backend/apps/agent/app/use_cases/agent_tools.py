"""RAG 검색 결과 → facts 직렬화 (`facts.news`가 쓴다).

v0.68.0(리포트 코드 우선 구조)에서 리포트 도구 루프를 걷어냈다 — 평가 252회에서 도구 호출 0회였고,
자금 계획은 별도 화면이다. 남은 것은 facts 수집이 쓰는 변환 하나다.
"""

from apps.rag.domain.entities.rag_chunk_entity import RagHit


def hit_to_dict(hit: RagHit) -> dict:
    return {
        "chunk_id": hit.chunk_id,
        "source_type": hit.source_type,
        "source_id": hit.source_id,
        "content": hit.content,
        "score": hit.score,
        "url": hit.url,
        "org": hit.org,
        "published_at": hit.published_at.isoformat() if hit.published_at else None,
    }
