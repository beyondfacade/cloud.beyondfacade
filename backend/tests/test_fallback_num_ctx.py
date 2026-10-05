"""로컬 폴백(gemma4:12b)은 num_ctx를 지정해야 한다 — Ollama 기본 컨텍스트(~2k 토큰)가 리포트 프롬프트를 자른다."""

import json

import httpx

from apps.agent.dependencies import analysis_dependencies
from apps.ops.adapter.outbound.gateways import llm_chain_gateway, probe_gateways


def _capture(bodies):
    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "ok"}, "done": True})
    return httpx.MockTransport(handler)


def _send(adapter):
    bodies = []
    adapter.client = httpx.Client(base_url="http://x", transport=_capture(bodies))
    adapter.chat([], [])
    return bodies[0]


def test_운영_로컬_폴백은_num_ctx_32768을_요청에_싣는다():
    body = _send(analysis_dependencies._local())
    assert body["model"] == "gemma4:12b" and body["options"]["num_ctx"] == 32768


def test_운영_점검_프로브_폴백도_같은_num_ctx를_싣는다(monkeypatch):
    built = {}

    class _FakeFallback:
        model_name = "fake"

        def __init__(self, primary, secondary, recorder):
            built["secondary"] = secondary

        def chat(self, messages, tools):
            raise RuntimeError("stop")

    monkeypatch.setattr(probe_gateways, "FallbackLLMAdapter", _FakeFallback)
    probe_gateways.LlmProbe().run("hi")
    body = _send(built["secondary"]())
    assert body["model"] == "gemma4:12b" and body["options"]["num_ctx"] == 32768


def test_분석_배선과_운영_점검의_폴백_num_ctx_상수가_같다():
    assert analysis_dependencies._LOCAL_NUM_CTX == llm_chain_gateway.FALLBACK_NUM_CTX
