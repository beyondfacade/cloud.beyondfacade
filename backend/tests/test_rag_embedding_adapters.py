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
