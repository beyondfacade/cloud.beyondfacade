from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from apps.ops.app.dtos.healthcare_dto import (
    HealthcareSnapshotDto,
    LlmRouteDto,
    OllamaStatusDto,
    ProbeResultDto,
    RequiredModelDto,
)
from apps.ops.app.dtos.ops_history_dto import OpsActorDto, UsageSeriesDto
from apps.ops.app.ports.input.healthcare_use_case import HealthcareUseCase, UnknownProbeKind
from apps.ops.app.ports.output.healthcare_port import (
    LlmCallPort,
    LlmChainPort,
    LlmUsagePort,
    OllamaStatusPort,
    ProbePort,
    RagStatsPort,
)
from apps.ops.app.ports.output.ops_audit_port import OpsAuditPort
from apps.ops.domain.services.usage_series import BUCKET_HOURS, build_series, hour_of_day, summarize_calls
from apps.ops.domain.services.usage_stats import summarize_usage

_RECENT_ANALYSES = 10
PROBE_RUN_ACTION = "probe.run"


def _has_model(names: list[str], wanted: str) -> bool:
    # ollama 태그 생략(`name` = `name:latest`)을 같은 모델로 본다
    candidates = {wanted, f"{wanted}:latest"} if ":" not in wanted else {wanted}
    return any(name in candidates for name in names)


class HealthcareInteractor(HealthcareUseCase):
    def __init__(
        self,
        ollama: OllamaStatusPort,
        chain: LlmChainPort,
        usage: LlmUsagePort,
        rag: RagStatsPort,
        probes: dict[str, ProbePort],
        calls: LlmCallPort,
        audit: OpsAuditPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._ollama = ollama
        self._chain = chain
        self._usage = usage
        self._rag = rag
        self._probes = probes
        self._calls = calls
        self._audit = audit
        self._clock = clock

    def myself(self) -> LlmRouteDto:
        return LlmRouteDto(role="primary", provider="myself", model="healthcare 배선 검증", available=True, detail="")

    def snapshot(self) -> HealthcareSnapshotDto:
        now = self._clock()
        ollama = self._ollama.read()
        week = self._usage.records_since(now - timedelta(days=7))
        day = self._usage.records_since(now - timedelta(hours=24))
        return HealthcareSnapshotDto(
            generated_at=now,
            llm_routes=[self._with_ollama(route, ollama) for route in self._chain.routes()],
            required_models=self._required_models(ollama),
            ollama=ollama,
            usage_24h=summarize_usage(day, window_hours=24),
            usage_7d=summarize_usage(week, window_hours=24 * 7),
            recent_analyses=self._usage.recent_analyses(_RECENT_ANALYSES),
            rag=self._rag.read(),
        )

    def probe(self, kind: str, message: str, actor: OpsActorDto) -> ProbeResultDto:
        probe = self._probes.get(kind)
        if probe is None:
            raise UnknownProbeKind(f"지원하지 않는 프로브: {kind}")
        result = probe.run(message)
        self._audit.record(actor, PROBE_RUN_ACTION, kind, f"{'성공' if result.ok else '실패'} · {result.latency_ms}ms")
        return result

    def usage_series(self, hours: int) -> UsageSeriesDto:
        now = self._clock()
        since = now - timedelta(hours=hours)
        usage = self._usage.timed_since(since)
        calls = self._calls.records_since(since)
        return UsageSeriesDto(
            generated_at=now,
            hours=hours,
            bucket_hours=BUCKET_HOURS[hours],
            points=build_series(usage, calls, now, hours),
            outcomes=summarize_calls(calls),
            by_hour=hour_of_day([row.at for row in usage]),
        )

    def _required_models(self, ollama: OllamaStatusDto) -> list[RequiredModelDto]:
        installed = [m.name for m in ollama.models]
        return [
            RequiredModelDto(
                name=name, purpose=purpose, installed=_has_model(installed, name), loaded=_has_model(ollama.loaded, name)
            )
            for name, purpose in self._chain.required_ollama_models()
        ]

    @staticmethod
    def _with_ollama(route: LlmRouteDto, ollama: OllamaStatusDto) -> LlmRouteDto:
        """로컬 경로의 가용성은 설정이 아니라 Ollama 실제 상태로 판정한다."""
        if route.provider != "ollama":
            return route
        if not ollama.reachable:
            return replace(route, available=False, detail="Ollama 연결 안 됨")
        if not _has_model([m.name for m in ollama.models], route.model):
            return replace(route, available=False, detail="모델 미설치")
        return replace(route, available=True, detail="설치됨")
