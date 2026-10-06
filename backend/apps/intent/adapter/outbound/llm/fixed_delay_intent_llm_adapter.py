"""부하 테스트용 가짜 의도 추출기 — IntentLlmPort 구현 (testplan §7-4 (c)).

정해진 시간만 쉬고 제안 없음(None)을 낸다 — 실제 LLM이 실패했을 때와 같은 경로로 관문이 마스터 사전만으로 답한다.
운영 배선에는 없다 — `LLM_MODE=fake`로 띄운 테스트 컨테이너에서만 쓴다.
"""

import time
from collections.abc import Callable

from apps.intent.app.dtos.intent_dto import LlmSuggestion
from apps.intent.app.ports.output.intent_port import IntentLlmPort

FIXED_DELAY_SECONDS = 3.0


class FixedDelayIntentLlmAdapter(IntentLlmPort):
    def __init__(self, delay_seconds: float = FIXED_DELAY_SECONDS, sleep: Callable[[float], None] = time.sleep) -> None:
        self._delay_seconds = delay_seconds
        self._sleep = sleep

    def extract(self, text: str) -> LlmSuggestion | None:
        self._sleep(self._delay_seconds)
        return None
