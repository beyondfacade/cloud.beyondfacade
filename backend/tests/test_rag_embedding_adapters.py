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


def test_ollama_qwen3_dim_인자가_요청_dimensions로_간다():
    captured = []
    OllamaQwen3EmbeddingAdapter(transport=_transport(captured), dim=2560).embed_documents(["문서"])
    assert captured[0]["dimensions"] == 2560


def test_gemini_기본값은_운영과_같다_001과_1536(monkeypatch):
    from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter

    adapter = GeminiEmbeddingAdapter(api_key="test-key")
    calls = []
    monkeypatch.setattr(
        adapter._client.models, "embed_content",
        lambda model, contents, config: calls.append((model, contents, config)) or _FakeEmbedResult(len(contents)),
    )
    adapter.embed_query("카페 지원")
    model, contents, config = calls[0]
    assert model == "gemini-embedding-001"
    assert contents == ["카페 지원"]
    assert config.task_type == "RETRIEVAL_QUERY"
    assert config.output_dimensionality == 1536


def test_gemini_2는_task_type_대신_프롬프트_프리픽스를_붙인다(monkeypatch):
    from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter

    adapter = GeminiEmbeddingAdapter(api_key="test-key", model="gemini-embedding-2", dim=3072)
    calls = []
    monkeypatch.setattr(
        adapter._client.models, "embed_content",
        lambda model, contents, config: calls.append((model, contents, config)) or _FakeEmbedResult(len(contents)),
    )
    adapter.embed_query("카페 지원")
    adapter.embed_documents(["청년 창업 자금\n서울시 지원"])
    assert adapter.model_name == "gemini-embedding-2"
    assert calls[0][1] == ["task: search result | query: 카페 지원"]
    assert calls[1][1] == ["title: 청년 창업 자금 | text: 청년 창업 자금\n서울시 지원"]
    assert calls[0][2].task_type is None
    assert calls[0][2].output_dimensionality == 3072


def test_gemini_429_재시도_횟수를_센다(monkeypatch):
    from google.genai import errors

    from apps.rag.adapter.outbound.embeddings import gemini_embedding_adapter as mod

    adapter = mod.GeminiEmbeddingAdapter(api_key="test-key")
    state = {"n": 0}

    def flaky(model, contents, config):
        state["n"] += 1
        if state["n"] == 1:
            raise errors.ClientError(429, {"error": {"message": "rate", "status": "RESOURCE_EXHAUSTED"}})
        return _FakeEmbedResult(len(contents))

    monkeypatch.setattr(adapter._client.models, "embed_content", flaky)
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    adapter.embed_query("q")
    assert adapter.retry_count == 1


def test_bge_m3는_프리픽스_없이_bge_m3_모델로_요청한다():
    from apps.rag.adapter.outbound.embeddings.ollama_bge_m3_adapter import OllamaBgeM3EmbeddingAdapter

    captured = []

    def handler(request):
        body = json.loads(request.content)
        captured.append(body)
        return httpx.Response(200, json={"embeddings": [[1.0] + [0.0] * 1023 for _ in body["input"]]})

    adapter = OllamaBgeM3EmbeddingAdapter(transport=httpx.MockTransport(handler))
    q = adapter.embed_query("카페 지원")
    docs = adapter.embed_documents([f"문서{i}" for i in range(120)])
    assert captured[0] == {"model": "bge-m3", "input": ["카페 지원"]}
    assert [len(c["input"]) for c in captured[1:]] == [50, 50, 20]
    assert len(q) == 1024 and len(docs) == 120
    assert adapter.model_name == "bge-m3" and adapter.provider == "ollama"
