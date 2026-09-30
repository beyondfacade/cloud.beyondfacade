from collections.abc import Callable
from datetime import UTC, datetime

from apps.ops.app.dtos.ops_history_dto import CollectorLogDto, CollectorRunDto, OpsActorDto
from apps.ops.app.errors import CollectorRunning, UnknownCollector
from apps.ops.app.ports.input.collector_tools_use_case import CollectorToolsUseCase
from apps.ops.app.ports.output.facility_port import CollectorLogPort, CollectorRunnerPort
from apps.ops.app.ports.output.ops_audit_port import OpsAuditPort
from apps.ops.domain.services.collector_catalog import COLLECTOR_BY_KEY, Collector
from apps.ops.domain.services.log_redaction import redact

COLLECTOR_RUN_ACTION = "collector.run"


class CollectorToolsInteractor(CollectorToolsUseCase):
    def __init__(
        self,
        logs: CollectorLogPort,
        runner: CollectorRunnerPort,
        audit: OpsAuditPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._logs = logs
        self._runner = runner
        self._audit = audit
        self._clock = clock

    def myself(self) -> CollectorLogDto:
        return CollectorLogDto(
            key="myself", log_file="myself.log", lines=["collector tools 배선 검증"], last_run_at=None, running=False
        )

    def log(self, key: str, lines: int) -> CollectorLogDto:
        collector = self._collector(key)
        return CollectorLogDto(
            key=key,
            log_file=collector.log_file,
            lines=[redact(line) for line in self._logs.tail(collector.log_file, lines)],
            last_run_at=self._logs.last_modified(collector.log_file),
            running=self._runner.is_running(key),
        )

    def run(self, key: str, actor: OpsActorDto) -> CollectorRunDto:
        collector = self._collector(key)
        if self._runner.is_running(key):
            raise CollectorRunning(f"{collector.label} 수집기가 이미 실행 중입니다.")
        self._runner.start(key)
        self._audit.record(actor, COLLECTOR_RUN_ACTION, key, collector.label)
        return CollectorRunDto(key=key, started_at=self._clock())

    @staticmethod
    def _collector(key: str) -> Collector:
        collector = COLLECTOR_BY_KEY.get(key)
        if collector is None:
            raise UnknownCollector(f"모르는 수집기입니다: {key}")
        return collector
