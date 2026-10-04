"""Ollama 주소 설정화 — 컨테이너가 OLLAMA_BASE_URL로 호스트 Ollama를 가리킬 수 있어야 한다."""

import httpx
import pytest

from apps.agent.adapter.outbound.llm.ollama_llm_adapter import OllamaLLMAdapter
from apps.ops.adapter.outbound.gateways.ollama_status_gateway import OllamaStatusGateway
from apps.rag.adapter.outbound.embeddings.ollama_bge_m3_adapter import OllamaBgeM3EmbeddingAdapter
from apps.rag.adapter.outbound.embeddings.ollama_qwen3_adapter import OllamaQwen3EmbeddingAdapter
from core.matrix.grid_keymaker_secret_manager import Settings, get_settings

HOST_URL = "http://host.docker.internal:11434"


@pytest.fixture
def host_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", HOST_URL)
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


def _client_url(client: httpx.Client) -> str:
    return str(client.base_url).rstrip("/")


def test_설정_기본값은_호스트_로컬_Ollama(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    assert Settings(_env_file=None).ollama_base_url == "http://127.0.0.1:11434"


@pytest.mark.parametrize(
    "build",
    [
        lambda **kw: OllamaLLMAdapter(**kw),
        lambda **kw: OllamaBgeM3EmbeddingAdapter(**kw),
        lambda **kw: OllamaQwen3EmbeddingAdapter(**kw),
    ],
)
def test_클라이언트는_환경변수_주소를_따른다(host_env, build):
    assert _client_url(build().client) == HOST_URL


@pytest.mark.parametrize(
    "build",
    [
        lambda **kw: OllamaLLMAdapter(**kw),
        lambda **kw: OllamaBgeM3EmbeddingAdapter(**kw),
        lambda **kw: OllamaQwen3EmbeddingAdapter(**kw),
    ],
)
def test_명시한_base_url이_환경변수보다_우선한다(host_env, build):
    assert _client_url(build(base_url="http://example.test:1").client) == "http://example.test:1"


def _refuse(request):
    raise httpx.ConnectError("refused")


def test_운영점검_게이트웨이는_해석된_주소를_보고한다(host_env):
    dto = OllamaStatusGateway(transport=httpx.MockTransport(_refuse)).read()
    assert dto.base_url == HOST_URL


def test_운영점검_게이트웨이는_명시한_주소가_우선한다(host_env):
    dto = OllamaStatusGateway(base_url="http://example.test:1", transport=httpx.MockTransport(_refuse)).read()
    assert dto.base_url == "http://example.test:1"
