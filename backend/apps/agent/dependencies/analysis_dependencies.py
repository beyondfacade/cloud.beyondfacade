"""Composition Root (DIP) — Agent 분석 UseCase·Repository 배선.

모델 선택(hybrid|opus|gemini|gemma3)은 Factory Method 레지스트리로 분기한다 (CLAUDE.md §5).
AnalysisInteractor.last_usage는 가변 인스턴스 상태이므로 요청마다 새 인스턴스를 만든다.
"""

from collections.abc import Callable

from apps.agent.adapter.outbound.gateways.event_analog_facts_gateway import (
    EventAnalogFactsGateway,
)
from apps.agent.adapter.outbound.gateways.finance_facts_gateway import FinanceFactsGateway
from apps.agent.adapter.outbound.gateways.funding_facts_gateway import FundingFactsGateway
from apps.agent.adapter.outbound.gateways.news_links_gateway import NewsLinksGateway
from apps.agent.adapter.outbound.gateways.question_budget_gateway import QuestionBudgetGateway
from apps.agent.adapter.outbound.gateways.region_facts_gateway import RegionFactsGateway
from apps.agent.adapter.outbound.gateways.regional_events_gateway import RegionalEventsGateway
from apps.agent.adapter.outbound.gateways.verdict_facts_gateway import VerdictFactsGateway
from apps.agent.adapter.outbound.llm.anthropic_llm_adapter import AnthropicLLMAdapter
from apps.agent.adapter.outbound.llm.fallback_llm_adapter import FallbackLLMAdapter
from apps.agent.adapter.outbound.llm.fixed_delay_llm_adapter import FixedDelayLLMAdapter
from apps.agent.adapter.outbound.llm.gemini_llm_adapter import GeminiLLMAdapter
from apps.agent.adapter.outbound.llm.ollama_llm_adapter import OllamaLLMAdapter
from apps.agent.adapter.outbound.repositories.analysis_pending_repository import (
    SqlAlchemyPendingAnalysisRepository,
)
from apps.agent.adapter.outbound.repositories.analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from apps.agent.adapter.outbound.repositories.llm_call_repository import SqlAlchemyLlmCallRecorder
from apps.agent.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.agent.app.ports.output.agent_port import LLMGatewayPort
from apps.agent.app.ports.output.analysis_pending_port import PendingAnalysisPort
from apps.agent.app.use_cases.analysis_interactor import AnalysisInteractor
from apps.agent.app.use_cases.report_facts import ReportFactsCollector
from apps.agent.domain.services.report_sampling import REPORT_SEED, REPORT_TEMPERATURE
from core.matrix.grid_keymaker_secret_manager import get_settings

# 로컬 폴백 컨텍스트 길이 — num_ctx를 안 주면 Ollama 0.31.2 기본값이 입력을 약 2k 토큰에서 잘라 읽는다.
# 해석 입력(사실 묶음 요약)은 약 2천 자지만 여유를 두어 32768로 올린다(벤치 2026-10-05, bge-m3와 동시 상주 9.8GB 실측).
# ops/adapter/outbound/gateways/llm_chain_gateway.py 의 FALLBACK_NUM_CTX 와 같아야 한다(테스트가 고정)
_LOCAL_NUM_CTX = 32768


# 모델 키 → LLM 어댑터 팩토리 (if/elif 대신 dict 디스패치)
# 참고: ollama gemma3:12b는 tools capability 없음 → 동일 패밀리 gemma4:12b로 배선
# 리포트 LLM은 Gemini·로컬 모두 온도 0·seed 고정 — 같은 질문에 일정한 답 (report_sampling 단일 원천)
def _local() -> LLMGatewayPort:
    return OllamaLLMAdapter(
        model="gemma4:12b", num_ctx=_LOCAL_NUM_CTX, temperature=REPORT_TEMPERATURE, seed=REPORT_SEED
    )


# 해석 모델 — 2026-10-06 평가(116건, opus 판정): gemini-3.8-flash 일반 6.9% · claude-opus-5-5 4.3%(구간 겹침) ·
# gemini-2.5-flash 16.5%. 3.8 일반이 오퍼스의 약 1/10 비용이라 1차, 오퍼스는 폴백(사용자 결정).
# ops/adapter/outbound/gateways/llm_chain_gateway.py 의 PRIMARY_MODEL·SECONDARY_MODEL 과 같아야 한다
REPORT_PRIMARY_MODEL = "gemini-3.8-flash"
REPORT_FALLBACK_MODEL = "claude-opus-5-5"


def _gemini() -> LLMGatewayPort:
    """키가 없으면 생성 시점에 ValueError — 폴백 어댑터가 그 예외로 키 유무를 판정한다. 3.8 Flash 일반 모드(사전 추론 끔)."""
    return GeminiLLMAdapter(model=REPORT_PRIMARY_MODEL, temperature=REPORT_TEMPERATURE, seed=REPORT_SEED)


def _opus() -> LLMGatewayPort:
    """키가 없으면 생성 시점에 ValueError. Opus 5.5는 생각을 끌 수 없어 effort low로 줄인다(온도는 받지 않는다)."""
    return AnthropicLLMAdapter(REPORT_FALLBACK_MODEL, effort="low")


def _opus_then_local() -> LLMGatewayPort:
    """오퍼스로 가되 키가 없거나 호출이 실패하면 로컬로 내려간다 — Gemini 다음 단계이자 가드 재시도 모델."""
    return FallbackLLMAdapter(primary=_opus, secondary=_local, recorder=SqlAlchemyLlmCallRecorder())


def _hybrid() -> LLMGatewayPort:
    """기본 배선 — Gemini 3.8 → 오퍼스 → 로컬. 어댑터는 키가 없으면 **생성 시점에** ValueError를 던지고,
    폴백 어댑터가 그 예외를 잡는 것이 곧 키 유무 판정이다 — 키 값을 읽지도 남기지도 않는다.
    """
    return FallbackLLMAdapter(primary=_gemini, secondary=_opus_then_local, recorder=SqlAlchemyLlmCallRecorder())


_LLM_REGISTRY: dict[str, Callable[[], LLMGatewayPort]] = {
    "hybrid": _hybrid,
    # 단일 모델 직접 지정은 남긴다 — 두뇌 비교 평가 러너(run_agent_eval)가 쓴다
    "gemma3": _local,
    "gemini": _gemini,
    "opus": _opus,
    # 부하 테스트 전용 — 고정 지연 가짜 LLM (testplan §7-4 (c))
    "fake": FixedDelayLLMAdapter,
}

# LLM_MODE=fake면 요청 본문이 어떤 모델을 골랐든 가짜 LLM — 부하 테스트 컨테이너에서 요금이 나가지 않게 (live는 그대로)
_MODE_OVERRIDE: dict[str, str] = {"fake": "fake"}

# 해석이 가드에 걸리면(판정 모순·숫자만 남은 단락) 다음 모델 — 운영 hybrid만 오퍼스(실패 시 로컬)로 한 번 더 쓴다(설계서 §5).
# 단일 모델 직접 지정(벤치·run_agent_eval)은 그 모델만 평가한다.
_RETRY_REGISTRY: dict[str, Callable[[], LLMGatewayPort]] = {"hybrid": _opus_then_local}


def build_analysis_use_case(model: str = "hybrid", budget: int | None = None) -> AnalysisUseCase:
    """요청 스코프 AnalysisInteractor — last_usage 누적이 요청 간에 섞이지 않게.

    세션 예산(원)은 facts 수집기에 심는다 — `facts.budget`이다(그래도 한다면 절의 자금 계획 안내).
    """
    model = _MODE_OVERRIDE.get(get_settings().llm_mode, model)
    try:
        llm_factory = _LLM_REGISTRY[model]
    except KeyError as error:
        raise ValueError(f"지원하지 않는 모델: {model}") from error
    facts = ReportFactsCollector(
        region_facts=RegionFactsGateway(),
        verdict_facts=VerdictFactsGateway(),
        funding_facts=FundingFactsGateway(),
        news_links=NewsLinksGateway(),
        analog_facts=EventAnalogFactsGateway(),
        finance_facts=FinanceFactsGateway(),
        question_budget=QuestionBudgetGateway(),
        regional_events=RegionalEventsGateway(),
    )
    retry = _RETRY_REGISTRY.get(model)
    return AnalysisInteractor(
        llm=llm_factory(), facts=facts, budget=budget, retry_llm=retry() if retry else None
    )


def get_analysis_use_case() -> AnalysisUseCase:
    """FastAPI Depends 기본 배선 — hybrid(Gemini 3.8 우선, 실패 시 오퍼스, 그다음 로컬)."""
    return build_analysis_use_case("hybrid")


def get_analysis_repository() -> SqlAlchemyAnalysisRepository:
    return SqlAlchemyAnalysisRepository()


def get_pending_analysis_port() -> PendingAnalysisPort:
    """대기 분석 장부 — Postgres라 워커가 여럿이어도 POST와 SSE가 같은 장부를 본다."""
    return SqlAlchemyPendingAnalysisRepository()
