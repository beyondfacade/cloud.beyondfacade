"""수집기 수동 실행 — 크론이 부르는 scripts/<key>.sh를 그대로 띄운다 (로그·잘라내기도 스크립트가 한다)."""

import subprocess
from pathlib import Path

from apps.ops.app.ports.output.facility_port import CollectorRunnerPort

_REPO_SCRIPTS = Path(__file__).resolve().parents[6] / "scripts"


class ScriptRunnerGateway(CollectorRunnerPort):
    def __init__(self, scripts_dir: Path = _REPO_SCRIPTS) -> None:
        self._scripts_dir = scripts_dir

    def is_running(self, key: str) -> bool:
        # 크론 실행도 수동 실행도 명령줄에 스크립트 경로가 들어간다
        result = subprocess.run(
            ["pgrep", "-f", f"scripts/{key}.sh"], capture_output=True, check=False, timeout=5
        )
        return result.returncode == 0

    def start(self, key: str) -> None:
        script = self._scripts_dir / f"{key}.sh"  # key는 유스케이스가 카탈로그로 검증한 값
        subprocess.Popen(
            ["bash", str(script)],
            cwd=self._scripts_dir.parent,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # API 워커가 재시작돼도 수집은 끝까지 간다
            close_fds=True,
        )
