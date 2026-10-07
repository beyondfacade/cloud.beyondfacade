"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.intent.adapter.outbound.gateways.master_dictionary_gateway import (
    MasterDictionaryGateway,
)
from apps.intent.adapter.outbound.gateways.profile_facts_gateway import ProfileFactsGateway
from apps.intent.adapter.outbound.llm.gemini_intent_llm_adapter import GeminiIntentLlmAdapter
from apps.intent.app.ports.input.intent_use_case import IntentUseCase
from apps.intent.app.use_cases.intent_interactor import IntentInteractor


def get_intent_use_case() -> IntentUseCase:
    masters = MasterDictionaryGateway()
    return IntentInteractor(
        masters=masters,
        facts=ProfileFactsGateway(),
        # 관문 LLM — 2026-10-07 같은 날 80건×3회 비교: 3.8 일반 동시 정답 98.8%·2.5 95.0%(지어내기 둘 다 0/26),
        # p93 4.4초 대 2.4초. 랜드마크 → 행정동 변환이 나아 3.8 일반 모드로(사용자 결정).
        llm=GeminiIntentLlmAdapter(masters, model="gemini-3.8-flash", thinking_off=True),
    )
