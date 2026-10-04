import time

import httpx

from apps.ops.app.dtos.healthcare_dto import OllamaModelDto, OllamaStatusDto
from apps.ops.app.ports.output.healthcare_port import OllamaStatusPort
from core.matrix.grid_keymaker_secret_manager import get_settings



class OllamaStatusGateway(OllamaStatusPort):
    def __init__(self, base_url: str | None = None, transport: httpx.BaseTransport | None = None) -> None:
        self._base_url = base_url or get_settings().ollama_base_url  # 에이전트·RAG Ollama 어댑터와 같은 설정
        self._client = httpx.Client(base_url=self._base_url, transport=transport, timeout=2.0)

    def read(self) -> OllamaStatusDto:
        started = time.perf_counter()
        try:
            tags = self._client.get("/api/tags")
            tags.raise_for_status()
            latency = round((time.perf_counter() - started) * 1000)
            running = self._client.get("/api/ps")
            loaded = [m["name"] for m in running.json().get("models", [])] if running.is_success else []
        except (httpx.HTTPError, ValueError) as error:
            return OllamaStatusDto(reachable=False, base_url=self._base_url, error=type(error).__name__)
        models = [OllamaModelDto(name=m["name"], size_bytes=m.get("size", 0)) for m in tags.json().get("models", [])]
        return OllamaStatusDto(
            reachable=True, base_url=self._base_url, latency_ms=latency, models=models, loaded=loaded
        )
