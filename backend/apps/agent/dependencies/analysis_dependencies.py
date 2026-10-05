"""Composition Root (DIP) — Agent 분석 UseCase·Repository 배선.

모델 선택(hybrid|gemini|gemma3)은 Factory Method 레지스트리로 분기한다 (CLAUDE.md §5).
AnalysisInteractor.last_usage는 가변 인스턴스 상태이므로 요청마다 새 인스턴스를 만든다.
"""

from collections.abc import Callable

from apps.agent.adapter.outbound.gateways.event_analog_facts_gateway import (
    EventAnalogFactsGateway,
)
from apps.agent.adapter.outbound.gateways.finance_facts_gateway import FinanceFactsGateway
from apps.agent.adapter.outbound.gateways.funding_facts_gateway import FundingFactsGateway
from apps.agent.adapter.outbound.gateways.region_facts_gateway import RegionFactsGateway
from apps.agent.adapter.outbound.gateways.verdict_facts_gateway import VerdictFactsGateway
from apps.agent.adapter.outbound.llm.fallback_llm_adapter import FallbackLLMAdapter
from apps.agent.adapter.outbound.llm.gemini_llm_adapter import GeminiLLMAdapter
from apps.agent.adapter.outbound.llm.ollama_llm_adapter import OllamaLLMAdapter
from apps.agent.adapter.outbound.repositories.analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from apps.agent.adapter.outbound.repositories.llm_call_repository import SqlAlchemyLlmCallRecorder
from apps.agent.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.agent.app.ports.output.agent_port import LLMGatewayPort
from apps.agent.app.use_cases.agent_tools import build_tools
from apps.agent.app.use_cases.analysis_interactor import AnalysisInteractor
from apps.agent.app.use_cases.report_facts import ReportFactsCollector
from apps.agent.domain.services.report_sampling import REPORT_SEED, REPORT_TEMPERATURE
from apps.rag.dependencies.rag_dependencies import get_rag_search_use_case

# 로컬 폴백 컨텍스트 길이 — num_ctx를 안 주면 Ollama 0.31.2 기본값이 입력을 약 2k 토큰에서 잘라 읽는다.
# 리포트 첫 턴 프롬프트는 도구 포함 최대 14.1k 토큰이라 32768로 올린다(벤치 2026-10-05, bge-m3와 동시 상주 9.8GB 실측).
# ops/adapter/outbound/gateways/llm_chain_gateway.py 의 FALLBACK_NUM_CTX 와 같아야 한다(테스트가 고정)
_LOCAL_NUM_CTX = 32768


# 모델 키 → LLM 어댑터 팩토리 (if/elif 대신 dict 디스패치)
# 참고: ollama gemma3:12b는 tools capability 없음 → 동일 패밀리 gemma4:12b로 배선
# 리포트 LLM은 Gemini·로컬 모두 온도 0·seed 고정 — 같은 질문에 일정한 답 (report_sampling 단일 원천)
def _local() -> LLMGatewayPort:
    return OllamaLLMAdapter(
        model="gemma4:12b", num_ctx=_LOCAL_NUM_CTX, temperature=REPORT_TEMPERATURE, seed=REPORT_SEED
    )


def _gemini() -> LLMGatewayPort:
    """키가 없으면 생성 시점에 ValueError — 폴백 어댑터가 그 예외로 키 유무를 판정한다."""
    return GeminiLLMAdapter(temperature=REPORT_TEMPERATURE, seed=REPORT_SEED)


def _hybrid() -> LLMGatewayPort:
    """기본 배선 — Gemini로 가되 키가 없거나 호출이 실패하면 로컬로 내려간다.

    GeminiLLMAdapter는 키가 없으면 **생성 시점에** ValueError를 던진다. 폴백 어댑터가 그
    예외를 잡는 것이 곧 키 유무 판정이다 — 키 값을 읽지도 남기지도 않는다.
    """
    return FallbackLLMAdapter(primary=_gemini, secondary=_local, recorder=SqlAlchemyLlmCallRecorder())


_LLM_REGISTRY: dict[str, Callable[[], LLMGatewayPort]] = {
    "hybrid": _hybrid,
    # 단일 모델 직접 지정은 남긴다 — 두뇌 비교 평가 러너(run_agent_eval)가 쓴다
    "gemma3": _local,
    "gemini": _gemini,
}


def build_analysis_use_case(model: str = "hybrid", budget: int | None = None) -> AnalysisUseCase:
    """요청 스코프 AnalysisInteractor — last_usage 누적이 요청 간에 섞이지 않게.

    세션 예산(원)은 여기서 도구와 facts 수집기 둘 다에 심는다 — finance 도구의 자기자본
    기본값이자 `facts.budget`이다(설계서 §5-2·§3-1).
    """
    try:
        llm_factory = _LLM_REGISTRY[model]
    except KeyError as error:
        raise ValueError(f"지원하지 않는 모델: {model}") from error
    region_facts = RegionFactsGateway()
    rag_search = get_rag_search_use_case()
    tools = build_tools(region_facts, rag_search, FinanceFactsGateway(), budget)
    facts = ReportFactsCollector(
        region_facts=region_facts,
        verdict_facts=VerdictFactsGateway(),
        funding_facts=FundingFactsGateway(),
        news_search=rag_search,
        analog_facts=EventAnalogFactsGateway(),
    )
    return AnalysisInteractor(llm=llm_factory(), tools=tools, facts=facts, budget=budget)


def get_analysis_use_case() -> AnalysisUseCase:
    """FastAPI Depends 기본 배선 — hybrid(Gemini 우선, 실패 시 로컬)."""
    return build_analysis_use_case("hybrid")


def get_analysis_repository() -> SqlAlchemyAnalysisRepository:
    return SqlAlchemyAnalysisRepository()
