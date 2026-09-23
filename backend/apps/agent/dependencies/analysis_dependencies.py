"""Composition Root (DIP) — Agent 분석 UseCase·Repository 배선.

모델 선택(hybrid|gemini|gemma3)은 Factory Method 레지스트리로 분기한다 (CLAUDE.md §5).
AnalysisInteractor.last_usage는 가변 인스턴스 상태이므로 요청마다 새 인스턴스를 만든다.
"""

from collections.abc import Callable

from apps.agent.adapter.outbound.gateways.finance_facts_gateway import FinanceFactsGateway
from apps.agent.adapter.outbound.gateways.region_facts_gateway import RegionFactsGateway
from apps.agent.adapter.outbound.llm.fallback_llm_adapter import FallbackLLMAdapter
from apps.agent.adapter.outbound.llm.gemini_llm_adapter import GeminiLLMAdapter
from apps.agent.adapter.outbound.llm.ollama_llm_adapter import OllamaLLMAdapter
from apps.agent.adapter.outbound.repositories.analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from apps.agent.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.agent.app.ports.output.agent_port import LLMGatewayPort
from apps.agent.app.use_cases.agent_tools import build_tools
from apps.agent.app.use_cases.analysis_interactor import AnalysisInteractor
from apps.rag.dependencies.rag_dependencies import get_rag_search_use_case

# 모델 키 → LLM 어댑터 팩토리 (if/elif 대신 dict 디스패치)
# 참고: ollama gemma3:12b는 tools capability 없음 → 동일 패밀리 gemma4:12b로 배선
def _local() -> LLMGatewayPort:
    return OllamaLLMAdapter(model="gemma4:12b")


def _hybrid() -> LLMGatewayPort:
    """기본 배선 — Gemini로 가되 키가 없거나 호출이 실패하면 로컬로 내려간다.

    GeminiLLMAdapter는 키가 없으면 **생성 시점에** ValueError를 던진다. 폴백 어댑터가 그
    예외를 잡는 것이 곧 키 유무 판정이다 — 키 값을 읽지도 남기지도 않는다.
    """
    return FallbackLLMAdapter(primary=GeminiLLMAdapter, secondary=_local)


_LLM_REGISTRY: dict[str, Callable[[], LLMGatewayPort]] = {
    "hybrid": _hybrid,
    # 단일 모델 직접 지정은 남긴다 — 두뇌 비교 평가 러너(run_agent_eval)가 쓴다
    "gemma3": _local,
    "gemini": GeminiLLMAdapter,
}


def build_analysis_use_case(model: str = "hybrid") -> AnalysisUseCase:
    """요청 스코프 AnalysisInteractor — last_usage 누적이 요청 간에 섞이지 않게."""
    try:
        llm_factory = _LLM_REGISTRY[model]
    except KeyError as error:
        raise ValueError(f"지원하지 않는 모델: {model}") from error
    tools = build_tools(RegionFactsGateway(), get_rag_search_use_case(), FinanceFactsGateway())
    return AnalysisInteractor(llm=llm_factory(), tools=tools)


def get_analysis_use_case() -> AnalysisUseCase:
    """FastAPI Depends 기본 배선 — hybrid(Gemini 우선, 실패 시 로컬)."""
    return build_analysis_use_case("hybrid")


def get_analysis_repository() -> SqlAlchemyAnalysisRepository:
    return SqlAlchemyAnalysisRepository()
