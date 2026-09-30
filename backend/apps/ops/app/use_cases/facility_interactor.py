import time
from collections.abc import Callable
from datetime import UTC, datetime

from apps.ops.app.dtos.facility_dto import (
    CollectorStatusDto,
    DatabaseStatusDto,
    FacilitySnapshotDto,
    ServiceCheckDto,
)
from apps.ops.app.ports.input.facility_use_case import FacilityUseCase
from apps.ops.app.ports.output.facility_port import (
    CollectorLogPort,
    DatabaseStatusPort,
    GpuMetricsPort,
    HostMetricsPort,
)
from apps.ops.app.ports.output.healthcare_port import OllamaStatusPort
from apps.ops.domain.services.collector_catalog import COLLECTORS, collector_status


class FacilityInteractor(FacilityUseCase):
    def __init__(
        self,
        host: HostMetricsPort,
        gpus: GpuMetricsPort,
        database: DatabaseStatusPort,
        ollama: OllamaStatusPort,
        logs: CollectorLogPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._host = host
        self._gpus = gpus
        self._database = database
        self._ollama = ollama
        self._logs = logs
        self._clock = clock

    def myself(self) -> ServiceCheckDto:
        return ServiceCheckDto(name="myself", ok=True, latency_ms=0, detail="facility 배선 검증")

    def snapshot(self) -> FacilitySnapshotDto:
        database, postgres = self._check_database()
        ollama = self._ollama.read()
        return FacilitySnapshotDto(
            generated_at=self._clock(),
            host=self._host.read(),
            gpus=self._gpus.read(),
            services=[
                postgres,
                ServiceCheckDto(
                    name="ollama",
                    ok=ollama.reachable,
                    latency_ms=ollama.latency_ms,
                    detail=f"모델 {len(ollama.models)}개 · 로드 {len(ollama.loaded)}개" if ollama.reachable else (ollama.error or "연결 안 됨"),
                ),
            ],
            database=database,
            collectors=self._collectors(database is not None),
        )

    def _check_database(self) -> tuple[DatabaseStatusDto | None, ServiceCheckDto]:
        started = time.perf_counter()
        try:
            database = self._database.read()
        except Exception as error:
            return None, ServiceCheckDto(name="postgres", ok=False, latency_ms=None, detail=type(error).__name__)
        latency = round((time.perf_counter() - started) * 1000)
        return database, ServiceCheckDto(name="postgres", ok=True, latency_ms=latency, detail=database.version)

    def _collectors(self, database_ok: bool) -> list[CollectorStatusDto]:
        now = self._clock()
        result = []
        for collector in COLLECTORS:
            last_run = self._logs.last_modified(collector.log_file)
            rows, latest = (
                self._database.table_stats(collector.table, collector.time_column)
                if database_ok and collector.table
                else (None, None)
            )
            result.append(
                CollectorStatusDto(
                    key=collector.key,
                    label=collector.label,
                    schedule=collector.schedule,
                    status=collector_status(last_run, collector.interval, now),
                    last_run_at=last_run,
                    table=collector.table,
                    rows=rows,
                    latest_data_at=latest,
                )
            )
        return result
