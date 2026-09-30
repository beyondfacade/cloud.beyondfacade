import os
from datetime import UTC, datetime
from pathlib import Path

from apps.ops.app.ports.output.facility_port import CollectorLogPort

_REPO_LOGS = Path(__file__).resolve().parents[6] / "logs"  # 크론 러너들이 쓰는 저장소 logs/
_TAIL_BYTES = 256 * 1024  # 꼬리만 읽는다 — 러너가 2000줄로 자르지만 한 줄이 길 수 있다


class CollectorLogGateway(CollectorLogPort):
    """크론 러너가 매 실행마다 로그를 덧붙이므로 로그 수정 시각 = 마지막 실행 시각."""

    def __init__(self, logs_dir: Path = _REPO_LOGS) -> None:
        self._logs_dir = logs_dir

    def last_modified(self, log_file: str) -> datetime | None:
        try:
            return datetime.fromtimestamp((self._logs_dir / log_file).stat().st_mtime, tz=UTC)
        except OSError:
            return None

    def tail(self, log_file: str, lines: int) -> list[str]:
        path = self._logs_dir / Path(log_file).name  # 카탈로그 값이지만 경로 이탈은 한 번 더 막는다
        try:
            with path.open("rb") as handle:
                size = handle.seek(0, os.SEEK_END)
                handle.seek(max(0, size - _TAIL_BYTES))
                chunk = handle.read()
        except OSError:
            return []
        text = chunk.decode("utf-8", errors="replace")
        rows = text.splitlines()
        if size > _TAIL_BYTES and rows:
            rows = rows[1:]  # 잘린 첫 줄은 버린다
        return rows[-lines:]
