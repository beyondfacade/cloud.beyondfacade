"""Ollama LLM 어댑터 옵션 — think·temperature는 줄 때만 요청에 실린다."""

import json

import httpx

from apps.agent.adapter.outbound.llm.ollama_llm_adapter import OllamaLLMAdapter


def _capture(bodies):
    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "ok"}, "done": True})
    return httpx.MockTransport(handler)


def test_기본값은_think와_options를_보내지_않는다():
    bodies = []
    OllamaLLMAdapter(model="m", base_url="http://x", transport=_capture(bodies)).chat([], [])
    assert "think" not in bodies[0] and "options" not in bodies[0]


def test_think와_temperature를_주면_실린다():
    bodies = []
    adapter = OllamaLLMAdapter(model="m", base_url="http://x", transport=_capture(bodies), think=False, temperature=0.3)
    adapter.chat([], [])
    assert bodies[0]["think"] is False and bodies[0]["options"] == {"temperature": 0.3}


def test_스트림도_같은_옵션을_싣는다():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, text='{"message":{"content":"a"},"done":true,"eval_count":1}\n')

    adapter = OllamaLLMAdapter(model="m", base_url="http://x", transport=httpx.MockTransport(handler), think=False, temperature=0.3)
    list(adapter.stream([], []))
    assert bodies[0]["think"] is False and bodies[0]["options"] == {"temperature": 0.3}


def test_num_ctx를_주면_options에_실린다():
    bodies = []
    adapter = OllamaLLMAdapter(model="m", base_url="http://x", transport=_capture(bodies), num_ctx=16384)
    adapter.chat([], [])
    assert bodies[0]["options"] == {"num_ctx": 16384}


def test_temperature와_num_ctx를_함께_싣는다():
    bodies = []
    adapter = OllamaLLMAdapter(model="m", base_url="http://x", transport=_capture(bodies), temperature=0.3, num_ctx=8192)
    adapter.chat([], [])
    assert bodies[0]["options"] == {"temperature": 0.3, "num_ctx": 8192}
