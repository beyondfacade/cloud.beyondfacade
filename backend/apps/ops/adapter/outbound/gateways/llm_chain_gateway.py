from apps.ops.app.dtos.healthcare_dto import LlmRouteDto
from apps.ops.app.ports.output.healthcare_port import LlmChainPort
from apps.rag.adapter.outbound.embeddings.ollama_bge_m3_adapter import OllamaBgeM3EmbeddingAdapter
from core.matrix.grid_keymaker_secret_manager import get_settings

# agent/dependencies/analysis_dependencies.py 의 hybrid 배선(_hybrid·_local)과 같아야 한다
PRIMARY_MODEL = "gemini-3.8-flash"
SECONDARY_MODEL = "claude-opus-5-5"
FALLBACK_MODEL = "gemma4:12b"
FALLBACK_NUM_CTX = 32768  # 기본 컨텍스트(~2k)는 리포트 프롬프트(13~14k)를 자른다 — _LOCAL_NUM_CTX와 같아야 한다


class LlmChainGateway(LlmChainPort):
    def routes(self) -> list[LlmRouteDto]:
        settings = get_settings()
        has_claude, has_gemini = bool(settings.anthropic_api_key), bool(settings.gemini_api_key)
        return [
            LlmRouteDto(
                role="primary",
                provider="gemini",
                model=PRIMARY_MODEL,
                available=has_gemini,
                detail="API 키 설정됨" if has_gemini else "API 키 없음 — 오퍼스로 폴백",
            ),
            LlmRouteDto(
                role="fallback",
                provider="anthropic",
                model=SECONDARY_MODEL,
                available=has_claude,
                detail="API 키 설정됨" if has_claude else "API 키 없음 — 로컬로 폴백",
            ),
            LlmRouteDto(role="fallback", provider="ollama", model=FALLBACK_MODEL, available=False, detail=""),
        ]

    def required_ollama_models(self) -> list[tuple[str, str]]:
        return [
            (FALLBACK_MODEL, "분석 폴백 LLM"),
            (OllamaBgeM3EmbeddingAdapter.OLLAMA_MODEL, "RAG 검색 임베딩"),
        ]
