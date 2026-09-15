"""Driving Ports — RagIndexUseCase·RagSearchUseCase 인터페이스 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.rag.domain.entities.rag_chunk_entity import RagHit


class RagIndexUseCase(ABC):
    @abstractmethod
    def index(self, full: bool = False) -> int:
        """원천 청크를 색인. 기본(full=False)은 증분(신규/미색인만), full=True는 전량 재색인.

        반환값은 처리(업서트)된 청크 건수.
        """


class RagSearchUseCase(ABC):
    @abstractmethod
    def search(
        self, query: str, top_k: int = 5, source_type: str | None = None
    ) -> list[RagHit]:
        """쿼리를 임베딩해 유사도 검색 — 상위 top_k개 결과 반환."""
