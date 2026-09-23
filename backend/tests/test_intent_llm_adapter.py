"""Gemini 폴백 어댑터 — 키가 없거나 호출이 실패하면 네트워크 없이 None (관문은 죽지 않는다)."""

from apps.intent.adapter.outbound.llm.gemini_intent_llm_adapter import GeminiIntentLlmAdapter
from tests.test_intent_interactor import FakeMasters


def test_키가_없으면_호출_없이_None이다():
    adapter = GeminiIntentLlmAdapter(FakeMasters(), api_key="")

    assert adapter.extract("홍대 근처 미용실") is None


def test_클라이언트가_예외를_던져도_None이다():
    adapter = GeminiIntentLlmAdapter(FakeMasters(), api_key="dummy")

    class Broken:
        class models:
            @staticmethod
            def generate_content(**_):
                raise TimeoutError("3s")

    adapter._client = Broken()

    assert adapter.extract("홍대 근처 미용실") is None
