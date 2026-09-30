from datetime import UTC, datetime
from pathlib import Path

from apps.ops.app.ports.output.facility_port import CollectorLogPort

_REPO_LOGS = Path(__file__).resolve().parents[6] / "logs"  # 크론 러너들이 쓰는 저장소 logs/


class CollectorLogGateway(CollectorLogPort):
    """크론 러너가 매 실행마다 로그를 덧붙이므로 로그 수정 시각 = 마지막 실행 시각."""

    def __init__(self, logs_dir: Path = _REPO_LOGS) -> None:
        self._logs_dir = logs_dir

    def last_modified(self, log_file: str) -> datetime | None:
        try:
            return datetime.fromtimestamp((self._logs_dir / log_file).stat().st_mtime, tz=UTC)
        except OSError:
            return None
