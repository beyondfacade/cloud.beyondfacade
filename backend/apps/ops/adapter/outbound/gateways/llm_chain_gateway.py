from apps.ops.app.dtos.healthcare_dto import LlmRouteDto
from apps.ops.app.ports.output.healthcare_port import LlmChainPort
from apps.rag.adapter.outbound.embeddings.ollama_qwen3_adapter import OllamaQwen3EmbeddingAdapter
from core.matrix.grid_keymaker_secret_manager import get_settings

# agent/dependencies/analysis_dependencies.py 의 hybrid 배선(_hybrid·_local)과 같아야 한다
PRIMARY_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemma4:12b"


class LlmChainGateway(LlmChainPort):
    def routes(self) -> list[LlmRouteDto]:
        has_key = bool(get_settings().gemini_api_key)
        return [
            LlmRouteDto(
                role="primary",
                provider="gemini",
                model=PRIMARY_MODEL,
                available=has_key,
                detail="API 키 설정됨" if has_key else "API 키 없음 — 로컬로 폴백",
            ),
            LlmRouteDto(role="fallback", provider="ollama", model=FALLBACK_MODEL, available=False, detail=""),
        ]

    def required_ollama_models(self) -> list[tuple[str, str]]:
        return [
            (FALLBACK_MODEL, "분석 폴백 LLM"),
            (OllamaQwen3EmbeddingAdapter.OLLAMA_MODEL, "RAG 검색 임베딩"),
        ]
