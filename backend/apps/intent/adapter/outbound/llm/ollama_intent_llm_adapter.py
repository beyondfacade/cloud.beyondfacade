"""Ollama 관문 추출기 — Gemini 폴백(`gemini_intent_llm_adapter`)과 같은 지시문·JSON 스키마를 로컬 모델로.

LLM 모델 평가(2026-10-04)용이며 운영 배선(intent_dependencies)에는 아직 넣지 않는다. 어떤 실패든 None —
관문은 LLM 장애로 죽지 않는다(IntentLlmPort 계약).
"""

import json
import logging

import httpx

from apps.intent.adapter.outbound.llm.gemini_intent_llm_adapter import INTENT_SCHEMA, instruction
from apps.intent.app.dtos.intent_dto import LlmSuggestion
from apps.intent.app.ports.output.intent_port import IntentLlmPort, MasterDictionaryPort
from core.matrix.grid_keymaker_secret_manager import get_settings

LOGGER = logging.getLogger("beyondfacade.intent.llm")


class OllamaIntentLlmAdapter(IntentLlmPort):
    def __init__(
        self,
        masters: MasterDictionaryPort,
        model: str,
        base_url: str | None = None,
        transport=None,
        think: bool | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self._masters = masters
        self.model_name = model
        self._think = think
        self._client = httpx.Client(
            base_url=base_url or get_settings().ollama_base_url, transport=transport, timeout=timeout_s
        )

    def extract(self, text: str) -> LlmSuggestion | None:
        try:
            body = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": instruction(self._masters.load())},
                    {"role": "user", "content": text},
                ],
                "format": INTENT_SCHEMA,
                "options": {"temperature": 0},
                "stream": False,
            }
            if self._think is not None:
                body["think"] = self._think
            response = self._client.post("/api/chat", json=body)
            response.raise_for_status()
            payload = json.loads(response.json()["message"]["content"])
            return LlmSuggestion(
                region_name=payload.get("region_name") or None,
                industry_id=payload.get("industry_id") or None,
                budget_krw=payload.get("budget_krw") or None,
            )
        except Exception as error:  # noqa: BLE001 — 폴백은 어떤 실패도 None으로 넘긴다
            LOGGER.warning("intent 로컬 LLM 실패: %s", error)
            return None
