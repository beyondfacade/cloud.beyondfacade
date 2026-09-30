from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from apps.ops.app.dtos.facility_dto import GpuDto, HostMetricsDto
from apps.ops.app.dtos.ops_history_dto import HostHistoryDto, HostPointDto
from apps.ops.app.ports.input.host_history_use_case import HostHistoryUseCase
from apps.ops.app.ports.output.facility_port import GpuMetricsPort, HostMetricsPort
from apps.ops.app.ports.output.host_sample_port import HostSampleRepositoryPort
from apps.ops.domain.entities.host_sample_entity import HostSample
from apps.ops.domain.services.host_history import SAMPLE_RETENTION, bucket_seconds, percent


def _to_point(sample: HostSample) -> HostPointDto:
    values = asdict(sample)
    return HostPointDto(t=values.pop("sampled_at"), **values)


def _sample_from(now: datetime, host: HostMetricsDto, gpus: list[GpuDto]) -> HostSample:
    memory_used = (
        host.memory_total_bytes - host.memory_available_bytes
        if host.memory_total_bytes is not None and host.memory_available_bytes is not None
        else None
    )
    root = host.disks[0] if host.disks else None
    gpu = gpus[0] if gpus else None  # 이 서버는 GPU 1장 — 여러 장이면 첫 장이 대표
    return HostSample(
        sampled_at=now.replace(second=0, microsecond=0),
        cpu_percent=host.cpu_percent,
        load1=host.load_avg[0] if host.load_avg else None,
        memory_percent=percent(memory_used, host.memory_total_bytes),
        swap_percent=percent(host.swap_used_bytes, host.swap_total_bytes),
        disk_percent=percent(root.used_bytes, root.total_bytes) if root else None,
        gpu_util_percent=float(gpu.utilization_percent) if gpu else None,
        gpu_memory_percent=percent(gpu.memory_used_mb, gpu.memory_total_mb) if gpu else None,
        gpu_temp_c=float(gpu.temperature_c) if gpu and gpu.temperature_c is not None else None,
    )


class HostHistoryInteractor(HostHistoryUseCase):
    def __init__(
        self,
        host: HostMetricsPort,
        gpus: GpuMetricsPort,
        samples: HostSampleRepositoryPort,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._host = host
        self._gpus = gpus
        self._samples = samples
        self._clock = clock

    def myself(self) -> HostHistoryDto:
        return HostHistoryDto(generated_at=datetime(2026, 9, 30, tzinfo=UTC), hours=24, bucket_seconds=360)

    def sample(self) -> tuple[HostPointDto, int]:
        now = self._clock()
        sample = _sample_from(now, self._host.read(), self._gpus.read())
        self._samples.add(sample)
        return _to_point(sample), self._samples.delete_before(now - SAMPLE_RETENTION)

    def history(self, hours: int) -> HostHistoryDto:
        now = self._clock()
        bucket = bucket_seconds(hours)
        samples = self._samples.series(now - timedelta(hours=hours), bucket)
        return HostHistoryDto(
            generated_at=now, hours=hours, bucket_seconds=bucket, points=[_to_point(s) for s in samples]
        )
