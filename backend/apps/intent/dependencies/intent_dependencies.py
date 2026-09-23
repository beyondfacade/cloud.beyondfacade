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
        llm=GeminiIntentLlmAdapter(masters),
    )
