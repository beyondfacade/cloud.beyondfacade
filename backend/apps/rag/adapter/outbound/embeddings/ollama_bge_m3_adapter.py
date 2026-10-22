"""Ollama bge-m3 임베딩 어댑터 — EmbeddingPort 구현 (1024차원 고정, instruction 없음).

Ollama가 정규화된 벡터를 돌려준다(2026-10-04 실측 노름 1.0, F16) — 여기서 다시 정규화하지 않는다.
"""

import httpx

from apps.rag.app.ports.output.rag_port import EmbeddingPort
from core.matrix.grid_keymaker_secret_manager import get_settings


class OllamaBgeM3EmbeddingAdapter(EmbeddingPort):
    MODEL_NAME = "bge-m3"
    PROVIDER = "ollama"
    OLLAMA_MODEL = "bge-m3"
    # 요청마다 문서 1개 — Ollama는 요청을 하나씩 처리해 50개 묶음(CPU 약 25초) 동안 화면 질의가 5초 타임아웃에 걸린다.
    # 1개씩이면 색인은 약 13% 느려지고 색인 중 질의 지연은 최대 0.7초(10/22 로컬 CPU 2코어 실측)
    BATCH_SIZE = 1

    def __init__(self, base_url: str | None = None, transport=None, timeout: float = 120.0):
        # 색인은 콜드스타트(모델 로드) 대비 120초(ollama_qwen3_adapter와 같음). 화면이 기다리는 질의 경로는 짧게 준다
        self.client = httpx.Client(base_url=base_url or get_settings().ollama_base_url, transport=transport, timeout=timeout)

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    @property
    def provider(self) -> str:
        return self.PROVIDER

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.BATCH_SIZE):
            response = self.client.post(
                "/api/embed", json={"model": self.OLLAMA_MODEL, "input": texts[start : start + self.BATCH_SIZE]}
            )
            response.raise_for_status()
            vectors.extend(response.json()["embeddings"])
        return vectors
