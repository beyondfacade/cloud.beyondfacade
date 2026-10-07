"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from collections.abc import Callable

from apps.intent.adapter.outbound.gateways.master_dictionary_gateway import (
    MasterDictionaryGateway,
)
from apps.intent.adapter.outbound.gateways.profile_facts_gateway import ProfileFactsGateway
from apps.intent.adapter.outbound.llm.fixed_delay_intent_llm_adapter import FixedDelayIntentLlmAdapter
from apps.intent.adapter.outbound.llm.gemini_intent_llm_adapter import GeminiIntentLlmAdapter
from apps.intent.app.ports.input.intent_use_case import IntentUseCase
from apps.intent.app.ports.output.intent_port import IntentLlmPort, MasterDictionaryPort
from apps.intent.app.use_cases.intent_interactor import IntentInteractor
from core.matrix.grid_keymaker_secret_manager import get_settings

# LLM_MODE → 의도 추출기 팩토리 — fake는 부하 테스트 전용 고정 지연 가짜 (testplan §7-4 (c))
# 관문 LLM(live) — 2026-10-07 같은 날 80건×3회 비교: 3.8 일반 동시 정답 98.8%·2.5 95.0%(지어내기 둘 다 0/26),
# p93 4.4초 대 2.4초. 랜드마크 → 행정동 변환이 나아 3.8 일반 모드로(사용자 결정).
_LLM_BY_MODE: dict[str, Callable[[MasterDictionaryPort], IntentLlmPort]] = {
    "live": lambda masters: GeminiIntentLlmAdapter(masters, model="gemini-3.8-flash", thinking_off=True),
    "fake": lambda _masters: FixedDelayIntentLlmAdapter(),
}


def get_intent_use_case() -> IntentUseCase:
    masters = MasterDictionaryGateway()
    return IntentInteractor(
        masters=masters,
        facts=ProfileFactsGateway(),
        llm=_LLM_BY_MODE[get_settings().llm_mode](masters),
    )
