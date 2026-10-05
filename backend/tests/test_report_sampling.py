"""리포트 LLM 샘플링(온도·seed) — 같은 질문에 일정한 답을 내도록 운영 배선이 단일 원천 상수를 쓴다.

모델·네트워크 없음: Ollama는 MockTransport, Gemini는 SDK Client 스텁.
"""

import json

import httpx

from apps.agent.adapter.outbound.llm import gemini_llm_adapter
from apps.agent.adapter.outbound.llm.gemini_llm_adapter import GeminiLLMAdapter
from apps.agent.adapter.outbound.llm.ollama_llm_adapter import OllamaLLMAdapter
from apps.agent.dependencies import analysis_dependencies
from apps.agent.domain.services.report_sampling import REPORT_SEED, REPORT_TEMPERATURE
from apps.ops.adapter.outbound.gateways import probe_gateways


class _Text:
    text = "ok"
    function_calls = None
    usage_metadata = None


class _Models:
    def __init__(self) -> None:
        self.configs: list = []

    def generate_content(self, *, model, contents, config):
        self.configs.append(config)
        return _Text()


def _gemini(monkeypatch, **kwargs) -> tuple[GeminiLLMAdapter, _Models]:
    models = _Models()
    monkeypatch.setattr(gemini_llm_adapter.genai, "Client", lambda **kw: type("C", (), {"models": models})())
    return GeminiLLMAdapter(api_key="stub-key", **kwargs), models


def _ollama_body(adapter: OllamaLLMAdapter) -> dict:
    bodies: list[dict] = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "ok"}, "done": True})

    adapter.client = httpx.Client(base_url="http://x", transport=httpx.MockTransport(handler))
    adapter.chat([], [])
    return bodies[0]


def test_리포트_샘플링_상수는_온도_0_seed_42다():
    assert (REPORT_TEMPERATURE, REPORT_SEED) == (0.0, 42)


def test_gemini는_온도와_seed를_지정하면_generationConfig에_싣는다(monkeypatch):
    adapter, models = _gemini(monkeypatch, temperature=0.0, seed=42)

    adapter.chat([{"role": "user", "content": "hi"}], [])

    assert (models.configs[0].temperature, models.configs[0].seed) == (0.0, 42)


def test_gemini는_지정하지_않으면_지금_요청과_같다(monkeypatch):
    adapter, models = _gemini(monkeypatch)

    adapter.chat([{"role": "user", "content": "hi"}], [])

    assert (models.configs[0].temperature, models.configs[0].seed) == (None, None)


def test_ollama는_seed를_지정하면_options에_싣고_아니면_싣지_않는다():
    assert _ollama_body(OllamaLLMAdapter(model="m", temperature=0.0, seed=42))["options"] == {
        "temperature": 0.0,
        "seed": 42,
    }
    assert "options" not in _ollama_body(OllamaLLMAdapter(model="m"))


def test_운영_리포트_배선은_gemini와_로컬_폴백_모두_상수를_쓴다(monkeypatch):
    built = {}

    class _FakeFallback:
        def __init__(self, primary, secondary, recorder):
            built.update(primary=primary, secondary=secondary)

    monkeypatch.setattr(analysis_dependencies, "FallbackLLMAdapter", _FakeFallback)
    monkeypatch.setattr(analysis_dependencies, "SqlAlchemyLlmCallRecorder", lambda: None)
    analysis_dependencies._hybrid()
    _, models = _gemini(monkeypatch)  # Client 스텁만 깐다

    built["primary"]().chat([{"role": "user", "content": "hi"}], [])
    body = _ollama_body(built["secondary"]())

    assert (models.configs[0].temperature, models.configs[0].seed) == (REPORT_TEMPERATURE, REPORT_SEED)
    assert body["options"] == {"temperature": REPORT_TEMPERATURE, "num_ctx": 32768, "seed": REPORT_SEED}


def test_단일_모델_직접_지정도_같은_상수를_쓴다(monkeypatch):
    _, models = _gemini(monkeypatch)

    analysis_dependencies._LLM_REGISTRY["gemini"]().chat([{"role": "user", "content": "hi"}], [])
    body = _ollama_body(analysis_dependencies._LLM_REGISTRY["gemma3"]())

    assert (models.configs[0].temperature, models.configs[0].seed) == (REPORT_TEMPERATURE, REPORT_SEED)
    assert body["options"]["seed"] == REPORT_SEED


def test_운영_점검_프로브도_리포트와_같은_샘플링을_쓴다(monkeypatch):
    built = {}

    class _FakeFallback:
        model_name = "fake"

        def __init__(self, primary, secondary, recorder):
            built.update(primary=primary, secondary=secondary)

        def chat(self, messages, tools):
            raise RuntimeError("stop")

    monkeypatch.setattr(probe_gateways, "FallbackLLMAdapter", _FakeFallback)
    probe_gateways.LlmProbe().run("hi")
    _, models = _gemini(monkeypatch)

    built["primary"]().chat([{"role": "user", "content": "hi"}], [])
    body = _ollama_body(built["secondary"]())

    assert (models.configs[0].temperature, models.configs[0].seed) == (REPORT_TEMPERATURE, REPORT_SEED)
    assert body["options"]["seed"] == REPORT_SEED and body["options"]["temperature"] == REPORT_TEMPERATURE
