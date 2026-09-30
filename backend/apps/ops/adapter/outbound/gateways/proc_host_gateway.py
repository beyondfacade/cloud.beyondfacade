"""리눅스 /proc 기반 호스트 지표 — psutil 없이 표준 라이브러리만. 도커 안에서는 컨테이너 관점 값이다."""

import os
import platform
import shutil
import socket
import time
from pathlib import Path

from apps.ops.app.dtos.facility_dto import DiskDto, HostMetricsDto
from apps.ops.app.ports.output.facility_port import HostMetricsPort

_CPU_SAMPLE_SECONDS = 0.1


def parse_meminfo(text: str) -> dict[str, int]:
    """`MemTotal:  16303424 kB` → {"MemTotal": 16694706176} (바이트)."""
    values = {}
    for line in text.splitlines():
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts and parts[0].isdigit():
            values[key] = int(parts[0]) * (1024 if len(parts) > 1 and parts[1] == "kB" else 1)
    return values


def cpu_busy_percent(before: list[int], after: list[int]) -> float | None:
    """/proc/stat 첫 줄 두 표본 사이 비유휴 비율. idle = idle + iowait."""
    deltas = [b - a for a, b in zip(before, after)]
    total = sum(deltas)
    if total <= 0:
        return None
    idle = deltas[3] + (deltas[4] if len(deltas) > 4 else 0)
    return round((total - idle) / total * 100, 1)


class ProcHostGateway(HostMetricsPort):
    def __init__(self, proc_root: Path = Path("/proc"), disk_paths: tuple[str, ...] = ("/",)) -> None:
        self._proc = proc_root
        self._disk_paths = disk_paths

    def read(self) -> HostMetricsDto:
        memory = parse_meminfo(self._read("meminfo") or "")
        swap_total = memory.get("SwapTotal")
        return HostMetricsDto(
            hostname=socket.gethostname(),
            platform=platform.platform(),
            cpu_count=os.cpu_count() or 1,
            cpu_percent=self._cpu_percent(),
            load_avg=[float(v) for v in (self._read("loadavg") or "0 0 0").split()[:3]],
            memory_total_bytes=memory.get("MemTotal"),
            memory_available_bytes=memory.get("MemAvailable"),
            swap_total_bytes=swap_total,
            swap_used_bytes=swap_total - memory.get("SwapFree", 0) if swap_total is not None else None,
            uptime_seconds=int(float(uptime.split()[0])) if (uptime := self._read("uptime")) else None,
            disks=[self._disk(path) for path in self._disk_paths],
        )

    def _read(self, name: str) -> str | None:
        try:
            return (self._proc / name).read_text()
        except OSError:
            return None

    def _cpu_sample(self) -> list[int] | None:
        stat = self._read("stat")
        return [int(v) for v in stat.splitlines()[0].split()[1:]] if stat else None

    def _cpu_percent(self) -> float | None:
        before = self._cpu_sample()
        if before is None:
            return None
        time.sleep(_CPU_SAMPLE_SECONDS)
        after = self._cpu_sample()
        return cpu_busy_percent(before, after) if after else None

    @staticmethod
    def _disk(path: str) -> DiskDto:
        usage = shutil.disk_usage(path)
        return DiskDto(mount=path, total_bytes=usage.total, used_bytes=usage.used, free_bytes=usage.free)
