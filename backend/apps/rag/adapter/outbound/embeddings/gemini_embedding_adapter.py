"""Gemini 임베딩 어댑터 — 온라인용 EmbeddingPort 구현.

1536차원 (foodrm 식품 법규 임베딩과 동일 규격).
"""

import logging
import time
from abc import ABC, abstractmethod

from google import genai
from google.genai import errors, types

from apps.rag.app.ports.output.rag_port import EmbeddingPort
from core.matrix.grid_keymaker_secret_manager import get_settings

LOGGER = logging.getLogger("beyondfacade.rag.embedding")

EMBEDDING_DIM = 1536


class _TaskFormat(ABC):
    """모델별 검색 작업 지시 방식 — 001은 task_type 파라미터, 2는 프롬프트 프리픽스(task_type 미지원)."""

    @abstractmethod
    def contents(self, texts: list[str], task_type: str) -> list[str]: ...

    @abstractmethod
    def config(self, task_type: str, dim: int) -> types.EmbedContentConfig: ...


class _TaskTypeParam(_TaskFormat):
    def contents(self, texts: list[str], task_type: str) -> list[str]:
        return texts

    def config(self, task_type: str, dim: int) -> types.EmbedContentConfig:
        return types.EmbedContentConfig(task_type=task_type, output_dimensionality=dim)


def _document_prefix(text: str) -> str:
    return f"title: {text.split(chr(10), 1)[0]} | text: {text}"


class _PromptPrefix(_TaskFormat):
    # ai.google.dev embeddings 문서(2026-10-04 확인)의 비대칭 검색 형식
    _PREFIX = {
        "RETRIEVAL_QUERY": lambda text: f"task: search result | query: {text}",
        "RETRIEVAL_DOCUMENT": _document_prefix,
    }

    def contents(self, texts: list[str], task_type: str) -> list[str]:
        return [self._PREFIX[task_type](t) for t in texts]

    def config(self, task_type: str, dim: int) -> types.EmbedContentConfig:
        return types.EmbedContentConfig(output_dimensionality=dim)


_TASK_FORMATS: dict[str, _TaskFormat] = {
    "gemini-embedding-001": _TaskTypeParam(),
    "gemini-embedding-2": _PromptPrefix(),
}
_GEMINI_BATCH_LIMIT = 100

# 429의 출처는 우리 호출량이 아니라 gemini-embedding 베이스 모델의 전역 공용 풀이다
# (global_embed_content_requests_per_minute_per_base_model). 2026-09-01 실측:
# 분당 20회에서 실패, 분당 164회 30연발은 전량 성공 — 분 단위 대기는 근거가 없다.
# 대개 1초 안에 풀리므로 짧게 시작하고, 긴 장애에도 촘촘히 재시도하도록 상한을 둔다.
_RETRY_BASE_DELAY = 0.5
_RETRY_MAX_DELAY = 4.0
_RETRY_BUDGET_SECONDS = 30.0


class GeminiEmbeddingAdapter(EmbeddingPort):
    """Gemini 임베딩 어댑터 — 쿼리 및 문서 벡터화 (배치 100 + 429 재시도)."""

    MODEL_NAME = "gemini-embedding-001"
    PROVIDER = "gemini"

    def __init__(self, api_key: str | None = None, model: str = MODEL_NAME, dim: int = EMBEDDING_DIM) -> None:
        self._client = genai.Client(api_key=api_key or get_settings().gemini_api_key)
        self._model = model
        self._dim = dim
        self._format = _TASK_FORMATS[model]
        self.retry_count = 0

    @property
    def model_name(self) -> str:
        """모델명."""
        return self._model

    @property
    def provider(self) -> str:
        """제공자."""
        return self.PROVIDER

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _GEMINI_BATCH_LIMIT):
            batch = texts[start : start + _GEMINI_BATCH_LIMIT]
            result = self._embed_batch_with_retry(batch, task_type)
            vectors.extend(e.values for e in result.embeddings)
        return vectors

    def _embed_batch_with_retry(self, batch: list[str], task_type: str):
        # 전역 공용 쿼터(429) 대비 — 지수 백오프로 예산 안에서 재시도
        waited = 0.0
        attempt = 0
        while True:
            try:
                return self._client.models.embed_content(
                    model=self.model_name,
                    contents=self._format.contents(batch, task_type),
                    config=self._format.config(task_type, self._dim),
                )
            except errors.ClientError as exc:
                delay = min(_RETRY_BASE_DELAY * 2**attempt, _RETRY_MAX_DELAY)
                if exc.code != 429 or waited + delay > _RETRY_BUDGET_SECONDS:
                    if exc.code == 429:
                        LOGGER.warning(
                            "임베딩 429 재시도 예산 %.1fs 소진 (%d회) — 호출부가 폴백한다",
                            waited,
                            attempt + 1,
                        )
                    raise
                time.sleep(delay)
                self.retry_count += 1
                waited += delay
                attempt += 1

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], task_type="RETRIEVAL_QUERY")[0]
