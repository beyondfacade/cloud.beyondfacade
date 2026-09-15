"""Driven Ports — RAG가 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from apps.rag.domain.entities.rag_chunk_entity import RagChunk, RagHit


class EmbeddingPort(ABC):
    """텍스트 임베딩 포트 — 쿼리 및 문서 벡터화."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """모델명 (예: qwen3-embedding-4b-q4)."""

    @property
    @abstractmethod
    def provider(self) -> str:
        """제공자 (예: ollama)."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """쿼리를 벡터화 — 검색용 임베딩 (프리픽스 포함)."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """문서 배치를 벡터화 — 인덱싱용 임베딩 (프리픽스 없음)."""


class RagSourcePort(ABC):
    """RAG 원천 데이터 포트 — 청크 순회 (Task 4-5에서 구현)."""

    @abstractmethod
    def iter_chunks(self) -> Iterator[RagChunk]:
        """원천 데이터를 청크 단위로 순회."""


class RagRepositoryPort(ABC):
    """RAG 저장소 포트 — 청크 저장 및 검색 (Task 5에서 구현)."""

    @abstractmethod
    def upsert_chunks(self, chunks: list[RagChunk]) -> int:
        """청크 배치 업서트 (신규 삽입, 기존 갱신) — 처리 건수 반환."""

    @abstractmethod
    def existing_ids(self, source_type: str) -> set[str]:
        """해당 source_type의 기존 청크 ID 집합 조회."""

    @abstractmethod
    def search(
        self,
        embedding: list[float],
        top_k: int,
        source_type: str | None = None,
        exclude_expired_funding: bool = True,
    ) -> list[RagHit]:
        """벡터 유사도 검색 — 상위 K개 결과 반환 (Task 5에서 구현)."""
