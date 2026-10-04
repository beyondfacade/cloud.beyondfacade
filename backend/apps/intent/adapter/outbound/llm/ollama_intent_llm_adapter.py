"""Ollama 관문 추출기 — Gemini 폴백(`gemini_intent_llm_adapter`)과 같은 지시문·JSON 스키마를 로컬 모델로.

LLM 모델 평가(2026-10-04)용이며 운영 배선(intent_dependencies)에는 아직 넣지 않는다. 어떤 실패든 None —
관문은 LLM 장애로 죽지 않는다(IntentLlmPort 계약).
"""

import json
import logging

import httpx

from apps.intent.adapter.outbound.llm.gemini_intent_llm_adapter import instruction
from apps.intent.app.dtos.intent_dto import LlmSuggestion
from apps.intent.app.ports.output.intent_port import IntentLlmPort, MasterDictionaryPort
from core.matrix.grid_keymaker_secret_manager import get_settings

LOGGER = logging.getLogger("beyondfacade.intent.llm")

# Ollama format은 JSON Schema다 — Gemini 표기 `nullable`을 무시해 모델이 문자열 "null"을 낸다(2026-10-04 실측).
OLLAMA_INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "region_name": {"type": ["string", "null"]},
        "industry_id": {"type": ["string", "null"]},
        "budget_krw": {"type": ["integer", "null"]},
    },
    "required": ["region_name", "industry_id", "budget_krw"],
}


def _text_or_none(value) -> str | None:
    """빈 값과 문자열 "null"(모델이 null 대신 내는 경우)은 None."""
    return None if not value or value == "null" else value


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
                "format": OLLAMA_INTENT_SCHEMA,
                "options": {"temperature": 0},
                "stream": False,
            }
            if self._think is not None:
                body["think"] = self._think
            response = self._client.post("/api/chat", json=body)
            response.raise_for_status()
            payload = json.loads(response.json()["message"]["content"])
            return LlmSuggestion(
                region_name=_text_or_none(payload.get("region_name")),
                industry_id=_text_or_none(payload.get("industry_id")),
                budget_krw=payload.get("budget_krw") or None,
            )
        except Exception as error:  # noqa: BLE001 — 폴백은 어떤 실패도 None으로 넘긴다
            LOGGER.warning("intent 로컬 LLM 실패: %s", error)
            return None
