"""파이프라인 프로브 — 운영 경로와 같은 배선을 실제로 한 번 태운다 (Strategy: kind → 프로브)."""

import time

from apps.agent.adapter.outbound.llm.fallback_llm_adapter import FallbackLLMAdapter
from apps.agent.adapter.outbound.llm.gemini_llm_adapter import GeminiLLMAdapter
from apps.agent.adapter.outbound.llm.ollama_llm_adapter import OllamaLLMAdapter
from apps.agent.adapter.outbound.repositories.llm_call_repository import SqlAlchemyLlmCallRecorder
from apps.agent.domain.services.report_sampling import REPORT_SEED, REPORT_TEMPERATURE
from apps.ops.adapter.outbound.gateways.llm_chain_gateway import FALLBACK_MODEL, FALLBACK_NUM_CTX, PRIMARY_MODEL
from apps.ops.app.dtos.healthcare_dto import ProbeHitDto, ProbeResultDto
from apps.ops.app.ports.output.healthcare_port import ProbePort
from apps.rag.dependencies.rag_dependencies import get_rag_search_use_case

_SNIPPET = 160
_OUTPUT = 600


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


class RagProbe(ProbePort):
    """운영 검색 배선(Ollama 쿼리 임베딩 → pgvector) 그대로 상위 5건."""

    def run(self, message: str) -> ProbeResultDto:
        started = time.perf_counter()
        try:
            hits = get_rag_search_use_case().search(message, top_k=5)
        except Exception as error:
            return ProbeResultDto(kind="rag", ok=False, latency_ms=_elapsed_ms(started), error=type(error).__name__)
        return ProbeResultDto(
            kind="rag",
            ok=True,
            latency_ms=_elapsed_ms(started),
            hits=[
                ProbeHitDto(
                    source_type=hit.source_type,
                    source_id=hit.source_id,
                    score=round(hit.score, 4),
                    snippet=hit.content[:_SNIPPET],
                    url=hit.url,
                )
                for hit in hits
            ],
        )


class LlmProbe(ProbePort):
    """분석 1차 모델(Gemini 3.8)에 도구 없이 한 턴 — 실패 시 로컬. 오퍼스 폴백 단계는 점검하지 않는다."""

    def run(self, message: str) -> ProbeResultDto:
        started = time.perf_counter()
        llm = FallbackLLMAdapter(
            # 리포트 배선(analysis_dependencies._hybrid)과 같은 샘플링 — 점검이 실제 리포트 호출을 재현하게
            primary=lambda: GeminiLLMAdapter(model=PRIMARY_MODEL, temperature=REPORT_TEMPERATURE, seed=REPORT_SEED),
            secondary=lambda: OllamaLLMAdapter(
                model=FALLBACK_MODEL, num_ctx=FALLBACK_NUM_CTX, temperature=REPORT_TEMPERATURE, seed=REPORT_SEED
            ),
            recorder=SqlAlchemyLlmCallRecorder(),
        )
        try:
            turn = llm.chat([{"role": "user", "content": message}], tools=[])
        except Exception as error:
            return ProbeResultDto(kind="llm", ok=False, latency_ms=_elapsed_ms(started), error=type(error).__name__)
        return ProbeResultDto(
            kind="llm",
            ok=True,
            latency_ms=_elapsed_ms(started),
            model=llm.model_name,
            output=turn.text[:_OUTPUT],
            input_tokens=turn.usage.input_tokens,
            output_tokens=turn.usage.output_tokens,
        )
