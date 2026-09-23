"""폴백 LLM 어댑터 — primary가 실패할 때만 secondary로 내려간다 (GoF Decorator).

두뇌 비교(`data/eval/results/agent_compare.md`, 시나리오 10)에서 5섹션 완성률이 로컬
gemma4:12b 50% · gemini-2.5-flash 90%, 평균 소요 39.9s · 17.4s였다. 그 측정은 도구 7종·
계약 블록 0개 시절이고 지금은 도구 9종 + 계약 블록 2개라 로컬 쪽 입력 토큰이 29,547까지
불어 더 나빠졌다. 그래서 기본은 Gemini다.

로컬을 버리지 않는 이유는 **키가 없는 환경**(도커 8200 조회 전용 컨테이너)과 쿼터 소진·
일시 장애다. 이 겹이 `if/elif` 없이 두 포트를 감싸 그 경우에만 내려가게 한다.

폴백하는 경우 — primary 어댑터 생성 실패(키 없음)·호출 예외(인증 오류·429 예산 소진·타임아웃).
폴백하지 **않는** 경우 — primary가 정상 응답했는데 내용이 빈약하거나 섹션이 모자란 것.
그건 장애가 아니라 품질이고, 여기서 판단할 일이 아니다.
"""

import logging
from collections.abc import Callable

from apps.agent.app.ports.output.agent_port import LLMGatewayPort, LLMToolSpec, LLMTurn

LOGGER = logging.getLogger("beyondfacade.agent.llm")


class FallbackLLMAdapter(LLMGatewayPort):
    """primary → (실패 시) secondary. 어느 쪽이 답했는지 `model_name`이 드러낸다."""

    def __init__(
        self,
        primary: Callable[[], LLMGatewayPort],
        secondary: Callable[[], LLMGatewayPort],
    ) -> None:
        self._primary_factory = primary
        self._secondary_factory = secondary
        self._primary: LLMGatewayPort | None = None
        self._secondary: LLMGatewayPort | None = None
        self._primary_unavailable = False  # 생성 실패(키 없음)는 턴마다 재시도하지 않는다
        # 아직 한 번도 호출하지 않았을 때의 표기 — 첫 chat()이 실제 값으로 덮는다
        self.model_name = "hybrid"

    def chat(self, messages: list[dict], tools: list[LLMToolSpec]) -> LLMTurn:
        primary = self._resolve_primary()
        if primary is not None:
            try:
                turn = primary.chat(messages, tools)
            except Exception as error:
                # 호출 실패는 매 턴 다시 시도한다 — 쿼터·일시 장애는 회복될 수 있다
                LOGGER.warning(
                    "primary LLM(%s) 호출 실패 — secondary로 폴백한다: %s",
                    primary.model_name,
                    type(error).__name__,
                )
            else:
                self.model_name = primary.model_name
                return turn

        secondary = self._resolve_secondary()
        turn = secondary.chat(messages, tools)
        self.model_name = secondary.model_name
        return turn

    def _resolve_primary(self) -> LLMGatewayPort | None:
        """생성이 한 번 실패하면(키 없음 등) 이후 턴에서는 만들지 않는다."""
        if self._primary_unavailable:
            return None
        if self._primary is None:
            try:
                self._primary = self._primary_factory()
            except Exception as error:
                self._primary_unavailable = True
                # 키 값은 읽지도 남기지도 않는다 — 예외 종류만 남긴다
                LOGGER.warning(
                    "primary LLM을 만들 수 없다(%s) — 이 요청은 secondary로만 간다",
                    type(error).__name__,
                )
                return None
        return self._primary

    def _resolve_secondary(self) -> LLMGatewayPort:
        if self._secondary is None:
            self._secondary = self._secondary_factory()
        return self._secondary
