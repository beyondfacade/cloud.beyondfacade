import time

import httpx

from apps.ops.app.dtos.healthcare_dto import OllamaModelDto, OllamaStatusDto
from apps.ops.app.ports.output.healthcare_port import OllamaStatusPort

_DEFAULT_BASE_URL = "http://127.0.0.1:11434"  # 에이전트·RAG Ollama 어댑터 기본값과 같다


class OllamaStatusGateway(OllamaStatusPort):
    def __init__(self, base_url: str = _DEFAULT_BASE_URL, transport: httpx.BaseTransport | None = None) -> None:
        self._base_url = base_url
        self._client = httpx.Client(base_url=base_url, transport=transport, timeout=2.0)

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
