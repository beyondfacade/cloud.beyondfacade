"""OllamaQwen3EmbeddingAdapter 임베딩 검증 — httpx.MockTransport 기반."""

import json

import httpx
import pytest

from apps.rag.adapter.outbound.embeddings.ollama_qwen3_adapter import (
    OllamaQwen3EmbeddingAdapter,
    QUERY_PROMPT,
)


def _transport(captured):
    """MockTransport: /api/embed 요청 바디 캡처."""
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"embeddings": [[3.0, 4.0] + [0.0] * 1534]})
    return httpx.MockTransport(handler)


def test_query_embedding_applies_instruct_prefix_and_dims():
    """embed_query: QUERY_PROMPT 프리픽스 + dimensions=1536."""
    captured = []
    adapter = OllamaQwen3EmbeddingAdapter(transport=_transport(captured))
    vec = adapter.embed_query("카페 지원")
    assert captured[0]["input"] == [QUERY_PROMPT + "카페 지원"]
    assert captured[0]["dimensions"] == 1536
    assert abs(sum(v * v for v in vec) - 1.0) < 1e-6  # L2 정규화


def test_document_embedding_has_no_prefix():
    """embed_documents: 프리픽스 없음."""
    captured = []
    OllamaQwen3EmbeddingAdapter(transport=_transport(captured)).embed_documents(["문서"])
    assert captured[0]["input"] == ["문서"]


def test_fp16_adapter_does_not_load_model_on_init():
    """Fp16Qwen3EmbeddingAdapter: 인스턴스 생성이 모델을 로드하지 않음 (GPU 미점유 원칙)."""
    pytest.importorskip("sentence_transformers")
    from apps.rag.adapter.outbound.embeddings.fp16_qwen3_adapter import Fp16Qwen3EmbeddingAdapter

    adapter = Fp16Qwen3EmbeddingAdapter()
    assert adapter._model is None
    assert adapter.model_name == "qwen3-embedding-4b-fp16"
    assert adapter.provider == "local"


class _FakeEmbedding:
    def __init__(self, values):
        self.values = values


class _FakeEmbedResult:
    def __init__(self, count):
        self.embeddings = [_FakeEmbedding([0.0] * 1536) for _ in range(count)]


def test_gemini_adapter_class_attributes():
    """GeminiEmbeddingAdapter: model_name·provider 확인."""
    from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter

    adapter = GeminiEmbeddingAdapter(api_key="test-key")
    assert adapter.model_name == "gemini-embedding-001"
    assert adapter.provider == "gemini"


def test_gemini_adapter_splits_250_inputs_into_3_batches(monkeypatch):
    """GeminiEmbeddingAdapter: 배치 100 제한 → 250개 입력이 3회 호출로 분할."""
    from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter

    adapter = GeminiEmbeddingAdapter(api_key="test-key")
    captured_batches = []

    def fake_embed_content(model, contents, config):
        captured_batches.append(contents)
        return _FakeEmbedResult(len(contents))

    monkeypatch.setattr(adapter._client.models, "embed_content", fake_embed_content)

    texts = [f"문서 {i}" for i in range(250)]
    vectors = adapter.embed_documents(texts)

    assert len(captured_batches) == 3
    assert [len(batch) for batch in captured_batches] == [100, 100, 50]
    assert len(vectors) == 250
