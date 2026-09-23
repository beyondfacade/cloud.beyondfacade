"""Gemini 폴백 추출기 — JSON 모드 1콜. 어떤 이유로든 실패하면 None (관문은 LLM 장애로 죽지 않는다).

agent BC의 `gemini_llm_adapter.py`와 같은 클라이언트·키 로딩을 쓰되 도구 호출·재시도 없이
짧게 한 번만 부른다(deadline은 API 최소값 10초). 랜드마크 사전을 두지 않는 대신 동 이름 427개를 프롬프트에 넣어 LLM이
"홍대 → 서교동"처럼 **마스터에 있는 이름으로만** 옮기게 한다. 그래도 최종 검증은 인터랙터가 한다.
"""

import json
import logging

from apps.intent.app.dtos.intent_dto import LlmSuggestion
from apps.intent.app.ports.output.intent_port import IntentLlmPort, MasterDictionaryPort
from core.matrix.grid_keymaker_secret_manager import get_settings

LOGGER = logging.getLogger("beyondfacade.intent.llm")

_TIMEOUT_MS = 10000  # Gemini가 허용하는 최소 deadline이 10초다 — 3초는 400 INVALID_ARGUMENT

_SCHEMA = {
    "type": "object",
    "properties": {
        "region_name": {"type": "string", "nullable": True},
        "industry_id": {"type": "string", "nullable": True},
        "budget_krw": {"type": "integer", "nullable": True},
    },
    "required": ["region_name", "industry_id", "budget_krw"],
}


class GeminiIntentLlmAdapter(IntentLlmPort):
    def __init__(
        self, masters: MasterDictionaryPort, model: str = "gemini-2.5-flash", api_key: str | None = None
    ) -> None:
        self._masters = masters
        self._model = model
        self._api_key = api_key if api_key is not None else get_settings().gemini_api_key
        self._client = None  # 키가 있을 때만, 첫 호출에서 만든다

    def extract(self, text: str) -> LlmSuggestion | None:
        if not self._api_key:
            return None
        try:
            from google import genai
            from google.genai import types

            if self._client is None:
                self._client = genai.Client(
                    api_key=self._api_key, http_options=types.HttpOptions(timeout=_TIMEOUT_MS)
                )
            dictionary = self._masters.load()
            response = self._client.models.generate_content(
                model=self._model,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=_instruction(dictionary),
                    response_mime_type="application/json",
                    response_schema=_SCHEMA,
                    temperature=0,
                ),
            )
            payload = json.loads(response.text or "{}")
            return LlmSuggestion(
                region_name=payload.get("region_name") or None,
                industry_id=payload.get("industry_id") or None,
                budget_krw=payload.get("budget_krw") or None,
            )
        except Exception as error:  # noqa: BLE001 — 폴백은 어떤 실패도 규칙 응답으로 넘긴다
            LOGGER.warning("intent LLM 폴백 실패 — 규칙 결과로 응답한다: %s", error)
            return None


def _instruction(dictionary) -> str:
    region_names = sorted({r.name for r in dictionary.regions})
    industries = ", ".join(f"{k}({v})" for k, v in dictionary.industry_names.items())
    return (
        "서울 창업 상담 문장에서 행정동·업종·예산을 뽑는다. JSON만 답한다.\n"
        "region_name은 아래 목록의 이름 그대로만 쓴다. 랜드마크·상권명(홍대·테헤란로·가로수길 등)은 "
        "그곳이 속한 행정동 이름으로 옮긴다. 확신이 없으면 null.\n"
        "industry_id는 아래 id 중 하나, 아니면 null. budget_krw는 원 단위 정수, 없으면 null.\n"
        f"업종: {industries}\n"
        f"행정동: {' '.join(region_names)}"
    )
