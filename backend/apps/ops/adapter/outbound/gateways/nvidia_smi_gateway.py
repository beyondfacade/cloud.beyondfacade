import shutil
import subprocess

from apps.ops.app.dtos.facility_dto import GpuDto
from apps.ops.app.ports.output.facility_port import GpuMetricsPort

_QUERY = "index,name,memory.used,memory.total,utilization.gpu,temperature.gpu"


def _int_or_none(value: str) -> int | None:
    return int(value) if value.strip().isdigit() else None


def parse_nvidia_smi(output: str) -> list[GpuDto]:
    gpus = []
    for line in output.strip().splitlines():
        index, name, used, total, util, temp = [part.strip() for part in line.split(",")]
        gpus.append(
            GpuDto(
                index=int(index),
                name=name,
                memory_used_mb=int(used),
                memory_total_mb=int(total),
                utilization_percent=_int_or_none(util) or 0,
                temperature_c=_int_or_none(temp),
            )
        )
    return gpus


class NvidiaSmiGateway(GpuMetricsPort):
    def read(self) -> list[GpuDto]:
        binary = shutil.which("nvidia-smi")
        if binary is None:
            return []
        try:
            completed = subprocess.run(
                [binary, f"--query-gpu={_QUERY}", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3, check=True,
            )
            return parse_nvidia_smi(completed.stdout)
        except (subprocess.SubprocessError, ValueError):
            return []
