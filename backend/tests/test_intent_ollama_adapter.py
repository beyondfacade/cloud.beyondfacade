"""로컬 관문 추출기 — Gemini와 같은 지시문·스키마를 Ollama format으로, 실패는 None."""

import json

import httpx

from apps.intent.adapter.outbound.llm.ollama_intent_llm_adapter import OLLAMA_INTENT_SCHEMA, OllamaIntentLlmAdapter
from tests.test_intent_interactor import FakeMasters  # 기존 테스트의 가짜 마스터를 재사용


def _adapter(handler, **kw):
    return OllamaIntentLlmAdapter(FakeMasters(), model="qwen3.5:4b", base_url="http://x", transport=httpx.MockTransport(handler), **kw)


def test_요청에_스키마와_temperature_0과_지시문이_실린다():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": '{"region_name":"서교동","industry_id":null,"budget_krw":null}'}})

    s = _adapter(handler, think=False).extract("홍대 근처")
    assert s.region_name == "서교동" and s.industry_id is None
    body = bodies[0]
    assert body["format"] == OLLAMA_INTENT_SCHEMA and body["options"] == {"temperature": 0} and body["think"] is False
    assert body["stream"] is False and body["messages"][0]["role"] == "system"


def test_스키마가_깨지면_None():
    s = _adapter(lambda r: httpx.Response(200, json={"message": {"content": "그냥 글"}})).extract("x")
    assert s is None


def test_서버_오류도_None():
    assert _adapter(lambda r: httpx.Response(500)).extract("x") is None


def test_문자열_null은_값으로_취급하지_않는다():
    content = '{"region_name":"null","industry_id":"null","budget_krw":0}'
    s = _adapter(lambda r: httpx.Response(200, json={"message": {"content": content}})).extract("x")
    assert s.region_name is None and s.industry_id is None and s.budget_krw is None
