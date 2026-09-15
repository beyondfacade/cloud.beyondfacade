"""fp16 로컬 임베딩 어댑터 — Qwen3-Embedding-4B (색인 전용, 새벽 배치).

- 출력 1536차원(MRL truncate) → vector(1536) 스키마와 호환.
- 모델 로딩(~8GB VRAM)은 첫 호출까지 지연 — FastAPI 임포트 시 GPU를 잡지 않는다.
- triton JIT에 C 컴파일러가 필요할 수 있다 — .env의 CC 참조 (docs/모델구성_v1.md).
"""

from apps.rag.app.ports.output.rag_port import EmbeddingPort

EMBEDDING_DIM = 1536


class Fp16Qwen3EmbeddingAdapter(EmbeddingPort):
    """fp16 Qwen3 임베딩 어댑터 — 색인(문서) 전용, 지연 로딩."""

    MODEL_NAME = "qwen3-embedding-4b-fp16"
    PROVIDER = "local"

    def __init__(self) -> None:
        self._model = None

    @property
    def model_name(self) -> str:
        """모델명."""
        return self.MODEL_NAME

    @property
    def provider(self) -> str:
        """제공자."""
        return self.PROVIDER

    def _load(self):
        if self._model is None:
            import torch
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                "Qwen/Qwen3-Embedding-4B",
                device="cuda" if torch.cuda.is_available() else "cpu",
                truncate_dim=EMBEDDING_DIM,
                model_kwargs={"torch_dtype": torch.float16},
            )
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # 법령 조문은 길이 편차가 커서 인코딩 배치를 보수적으로 잡는다 (VRAM 스파이크 방지)
        vectors = self._load().encode(texts, batch_size=8, normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vectors = self._load().encode([text], prompt_name="query", normalize_embeddings=True)
        return vectors[0].tolist()
