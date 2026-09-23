"""Composition Root (DIP) — Agent 분석 UseCase·Repository 배선.

모델 선택(gemma3|gemini)은 Factory Method 레지스트리로 분기한다 (CLAUDE.md §5).
AnalysisInteractor.last_usage는 가변 인스턴스 상태이므로 요청마다 새 인스턴스를 만든다.
"""

from collections.abc import Callable

from apps.agent.adapter.outbound.gateways.finance_facts_gateway import FinanceFactsGateway
from apps.agent.adapter.outbound.gateways.region_facts_gateway import RegionFactsGateway
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
_LLM_REGISTRY: dict[str, Callable[[], LLMGatewayPort]] = {
    "gemma3": lambda: OllamaLLMAdapter(model="gemma4:12b"),
    "gemini": GeminiLLMAdapter,
}


def build_analysis_use_case(model: str = "gemma3") -> AnalysisUseCase:
    """요청 스코프 AnalysisInteractor — last_usage 누적이 요청 간에 섞이지 않게."""
    try:
        llm_factory = _LLM_REGISTRY[model]
    except KeyError as error:
        raise ValueError(f"지원하지 않는 모델: {model}") from error
    tools = build_tools(RegionFactsGateway(), get_rag_search_use_case(), FinanceFactsGateway())
    return AnalysisInteractor(llm=llm_factory(), tools=tools)


def get_analysis_use_case() -> AnalysisUseCase:
    """FastAPI Depends 기본 배선 — gemma3."""
    return build_analysis_use_case("gemma3")


def get_analysis_repository() -> SqlAlchemyAnalysisRepository:
    return SqlAlchemyAnalysisRepository()
