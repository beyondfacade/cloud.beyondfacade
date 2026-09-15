"""Ollama Qwen3 임베딩 어댑터 — EmbeddingPort 구현."""

import httpx

from apps.rag.app.ports.output.rag_port import EmbeddingPort

QUERY_PROMPT = "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "


class OllamaQwen3EmbeddingAdapter(EmbeddingPort):
    """Ollama Qwen3 임베딩 어댑터 (쿼리 및 문서 벡터화)."""

    MODEL_NAME = "qwen3-embedding-4b-q4"
    PROVIDER = "ollama"
    OLLAMA_MODEL = "qwen3-embedding:4b"
    DIMENSIONS = 1536
    BATCH_SIZE = 50

    def __init__(self, base_url: str = "http://127.0.0.1:11434", transport=None):
        """
        Ollama 임베딩 어댑터 초기화.

        Args:
            base_url: Ollama 서버 URL (기본값: http://127.0.0.1:11434)
            transport: httpx.Transport (테스트용 MockTransport 주입 가능)
        """
        self.base_url = base_url
        # 기본 httpx 타임아웃(5s)은 콜드스타트(모델 로드·GPU 상주 모델 교체) 실측 초과 —
        # 색인 배치는 최초 요청에서 모델 로딩을 겸하므로 넉넉히 잡는다.
        self.client = httpx.Client(base_url=base_url, transport=transport, timeout=120.0)

    @property
    def model_name(self) -> str:
        """모델명."""
        return self.MODEL_NAME

    @property
    def provider(self) -> str:
        """제공자."""
        return self.PROVIDER

    def embed_query(self, text: str) -> list[float]:
        """
        쿼리를 벡터화 — 검색용 임베딩 (QUERY_PROMPT 프리픽스 포함).

        Args:
            text: 쿼리 텍스트

        Returns:
            L2 정규화된 벡터
        """
        prefixed_text = QUERY_PROMPT + text
        embeddings = self._embed_batch([prefixed_text])
        return embeddings[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        문서 배치를 벡터화 — 인덱싱용 임베딩 (프리픽스 없음).

        Args:
            texts: 문서 텍스트 배치

        Returns:
            L2 정규화된 벡터 배치
        """
        return self._embed_batch(texts)

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        배치 임베딩 (50개씩 분할 요청).

        Args:
            texts: 텍스트 배치

        Returns:
            L2 정규화된 벡터 배치
        """
        all_embeddings = []

        # 50개씩 분할해서 요청
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i : i + self.BATCH_SIZE]
            response = self.client.post(
                "/api/embed",
                json={
                    "model": self.OLLAMA_MODEL,
                    "input": batch,
                    "dimensions": self.DIMENSIONS,
                },
            )
            response.raise_for_status()

            data = response.json()
            embeddings = data.get("embeddings", [])

            # L2 정규화
            for embedding in embeddings:
                normalized = self._l2_normalize(embedding)
                all_embeddings.append(normalized)

        return all_embeddings

    @staticmethod
    def _l2_normalize(vector: list[float]) -> list[float]:
        """
        L2 정규화 (벡터의 크기를 1로 만듦).

        Args:
            vector: 입력 벡터

        Returns:
            정규화된 벡터
        """
        norm = sum(v * v for v in vector) ** 0.5
        if norm < 1e-10:
            return vector  # 제로 벡터는 그대로 반환
        return [v / norm for v in vector]
