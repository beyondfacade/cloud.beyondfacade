"""설비 추세·LLM 시계열·수집기 로그/수동 실행 API — 실제 테스트 DB, 가짜 호스트·실행기."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from apps.ops.adapter.outbound.gateways.admin_audit_gateway import AdminAuditGateway
from apps.ops.adapter.outbound.gateways.collector_log_gateway import CollectorLogGateway
from apps.ops.adapter.outbound.repositories.host_sample_repository import SqlAlchemyHostSampleRepository
from apps.ops.app.dtos.facility_dto import DiskDto, GpuDto, HostMetricsDto
from apps.ops.app.ports.output.facility_port import CollectorRunnerPort, GpuMetricsPort, HostMetricsPort
from apps.ops.app.use_cases.collector_tools_interactor import CollectorToolsInteractor
from apps.ops.app.use_cases.host_history_interactor import HostHistoryInteractor
from apps.ops.dependencies.ops_dependencies import get_collector_tools_use_case, get_host_history_use_case
from apps.ops.domain.entities.host_sample_entity import HostSample
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

PASSWORD = "correct-horse-battery"
CLIENT = ("198.51.100.20", 50000)
GiB = 1024**3


class _FixedHost(HostMetricsPort):
    def read(self) -> HostMetricsDto:
        return HostMetricsDto(
            hostname="h", platform="linux", cpu_count=8, cpu_percent=12.5, load_avg=[1.5, 1.0, 0.5],
            memory_total_bytes=16 * GiB, memory_available_bytes=4 * GiB, swap_total_bytes=2 * GiB,
            swap_used_bytes=GiB // 2, uptime_seconds=60,
            disks=[DiskDto(mount="/", total_bytes=100 * GiB, used_bytes=40 * GiB, free_bytes=60 * GiB)],
        )


class _OneGpu(GpuMetricsPort):
    def read(self) -> list[GpuDto]:
        return [GpuDto(index=0, name="RTX", memory_used_mb=4096, memory_total_mb=16384, utilization_percent=30, temperature_c=55)]


class _FakeRunner(CollectorRunnerPort):
    def __init__(self) -> None:
        self.running: set[str] = set()
        self.started: list[str] = []

    def is_running(self, key: str) -> bool:
        return key in self.running

    def start(self, key: str) -> None:
        self.started.append(key)
        self.running.add(key)


@pytest.fixture
def runner() -> _FakeRunner:
    return _FakeRunner()


@pytest.fixture(autouse=True)
def fakes(tmp_path: Path, runner: _FakeRunner):
    with session_scope() as session:
        session.execute(
            text(
                "truncate access_event, ip_block, admin_session, admin_audit, admin_user, host_metric_sample, "
                "llm_call_event restart identity cascade"
            )
        )
    get_admin_user_use_case().upsert("ops", PASSWORD, "operator")
    get_admin_user_use_case().upsert("viewer", PASSWORD, "viewer")
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "funding-collector.log").write_text(
        "".join(f"[05:10:{n:02d}] 줄 {n}\n" for n in range(30))
        + "GET https://apis.data.go.kr/x?serviceKey=REALKEY123&pageNo=1 실패\n"
    )
    app.dependency_overrides[get_host_history_use_case] = lambda: HostHistoryInteractor(
        host=_FixedHost(), gpus=_OneGpu(), samples=SqlAlchemyHostSampleRepository()
    )
    app.dependency_overrides[get_collector_tools_use_case] = lambda: CollectorToolsInteractor(
        logs=CollectorLogGateway(logs_dir=logs), runner=runner, audit=AdminAuditGateway()
    )
    yield
    app.dependency_overrides.clear()


def _client(username: str) -> TestClient:
    client = TestClient(app, client=CLIENT)
    assert client.post("/admin/auth/login", json={"username": username, "password": PASSWORD}).status_code == 200
    return client


def _audit_actions() -> list[tuple[str, str]]:
    with session_scope() as session:
        return [tuple(r) for r in session.execute(text("select action, target from admin_audit order by id"))]


# ── 설비 추세 ─────────────────────────────────────────


def test_표본은_지표를_비율로_정규화해_분_단위로_저장한다():
    use_case = HostHistoryInteractor(host=_FixedHost(), gpus=_OneGpu(), samples=SqlAlchemyHostSampleRepository())
    point, _ = use_case.sample()
    assert (point.cpu_percent, point.load1, point.memory_percent) == (12.5, 1.5, 75.0)
    assert (point.swap_percent, point.disk_percent) == (25.0, 40.0)
    assert (point.gpu_util_percent, point.gpu_memory_percent, point.gpu_temp_c) == (30.0, 25.0, 55.0)
    assert point.t.second == 0
    use_case.sample()  # 같은 분에 두 번 돌아도 한 행
    with session_scope() as session:
        assert session.execute(text("select count(*) from host_metric_sample")).scalar_one() == 1


def test_표본_적재는_8일_지난_표본을_지운다():
    repository = SqlAlchemyHostSampleRepository()
    repository.add(HostSample(sampled_at=datetime.now(UTC) - timedelta(days=9), cpu_percent=1.0))
    _, pruned = HostHistoryInteractor(host=_FixedHost(), gpus=_OneGpu(), samples=repository).sample()
    assert pruned == 1


def test_추세는_버킷_평균이고_오래된_것부터다():
    repository = SqlAlchemyHostSampleRepository()
    base = datetime.now(UTC).replace(second=0, microsecond=0) - timedelta(minutes=30)
    for minute, cpu in ((0, 10.0), (1, 20.0), (20, 50.0)):
        repository.add(HostSample(sampled_at=base + timedelta(minutes=minute), cpu_percent=cpu))
    body = _client("viewer").get("/admin/facility/history", params={"hours": 1}).json()
    assert body["bucket_seconds"] == 60
    assert [p["cpu_percent"] for p in body["points"]] == [10.0, 20.0, 50.0]
    week = _client("viewer").get("/admin/facility/history", params={"hours": 168}).json()
    assert week["bucket_seconds"] == 2520
    assert len(week["points"]) <= 2


def test_추세는_로그인이_필요하고_허용된_창만_받는다():
    assert TestClient(app).get("/admin/facility/history").status_code == 401
    assert TestClient(app).get("/admin/facility/history/myself").status_code == 200
    assert _client("viewer").get("/admin/facility/history", params={"hours": 5}).status_code == 422


# ── LLM 시계열 ────────────────────────────────────────


def test_사용_시계열은_호출_결과와_폴백률을_담는다():
    now = datetime.now(UTC)
    with session_scope() as session:
        for minutes, outcome in ((10, "fallback"), (9, "ok"), (120, "error"), (60 * 30, "ok")):
            session.execute(
                text(
                    "insert into llm_call_event (occurred_at, model, outcome, latency_ms) values (:at, 'm', :o, 100)"
                ),
                {"at": now - timedelta(minutes=minutes), "o": outcome},
            )
    body = _client("viewer").get("/admin/healthcare/usage-series").json()
    assert (body["hours"], body["bucket_hours"], len(body["points"])) == (24, 1, 24)
    assert body["outcomes"] == {
        "attempts": 3, "ok": 1, "fallback": 1, "error": 1, "fallback_rate": 0.3333, "error_rate": 0.3333,
    }
    assert len(body["by_hour"]) == 24
    assert sum(p["ok"] + p["fallback"] + p["error"] for p in body["points"]) == 3
    week = _client("viewer").get("/admin/healthcare/usage-series", params={"hours": 168}).json()
    assert (week["bucket_hours"], week["outcomes"]["attempts"]) == (6, 4)


def test_사용_시계열은_24와_168시간만_받는다():
    assert _client("viewer").get("/admin/healthcare/usage-series", params={"hours": 48}).status_code == 422


# ── 수집기 로그·수동 실행 ─────────────────────────────


def test_수집기_로그는_꼬리만_비밀값을_가려_돌려준다():
    body = _client("ops").get("/admin/facility/collectors/funding-collector/log", params={"lines": 10}).json()
    assert len(body["lines"]) == 10
    assert "REALKEY123" not in body["lines"][-1]
    assert "serviceKey=***" in body["lines"][-1]
    assert body["running"] is False
    assert body["last_run_at"] is not None


def test_수집기_로그와_실행은_운영_관리자만():
    viewer = _client("viewer")
    assert viewer.get("/admin/facility/collectors/funding-collector/log").status_code == 403
    assert viewer.post("/admin/facility/collectors/funding-collector/run").status_code == 403


def test_카탈로그에_없는_수집기는_404다():
    response = _client("ops").get("/admin/facility/collectors/rm-rf/log")
    assert (response.status_code, response.json()["error"]["code"]) == (404, "UNKNOWN_COLLECTOR")
    assert _client("ops").post("/admin/facility/collectors/..%2Fetc/run").status_code == 404


def test_수동_실행은_202이고_감사에_남으며_실행_중이면_409다(runner: _FakeRunner):
    ops = _client("ops")
    response = ops.post("/admin/facility/collectors/funding-collector/run")
    assert response.status_code == 202
    assert runner.started == ["funding-collector"]
    assert _audit_actions() == [("collector.run", "funding-collector")]
    again = ops.post("/admin/facility/collectors/funding-collector/run")
    assert (again.status_code, again.json()["error"]["code"]) == (409, "COLLECTOR_RUNNING")
    assert runner.started == ["funding-collector"]


def test_없는_로그_파일은_빈_꼬리다(tmp_path: Path):
    assert CollectorLogGateway(logs_dir=tmp_path).tail("none.log", 10) == []
