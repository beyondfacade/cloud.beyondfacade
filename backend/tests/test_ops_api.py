"""헬스케어실·설비실 API + 게이트웨이 — 네트워크·파일시스템·GPU 경계만 가짜로 바꾼다."""

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from apps.ops.adapter.outbound.gateways.collector_log_gateway import CollectorLogGateway
from apps.ops.adapter.outbound.gateways.llm_chain_gateway import LlmChainGateway
from apps.ops.adapter.outbound.gateways.llm_usage_gateway import LlmUsageGateway
from apps.ops.adapter.outbound.gateways.nvidia_smi_gateway import parse_nvidia_smi
from apps.ops.adapter.outbound.gateways.ollama_status_gateway import OllamaStatusGateway
from apps.ops.adapter.outbound.gateways.postgres_status_gateway import PostgresStatusGateway
from apps.ops.adapter.outbound.gateways.proc_host_gateway import ProcHostGateway, cpu_busy_percent, parse_meminfo
from apps.ops.adapter.outbound.gateways.rag_stats_gateway import RagStatsGateway
from apps.ops.app.dtos.facility_dto import GpuDto
from apps.ops.app.dtos.healthcare_dto import ProbeResultDto
from apps.ops.app.ports.output.facility_port import GpuMetricsPort
from apps.ops.app.ports.output.healthcare_port import ProbePort
from apps.ops.app.use_cases.facility_interactor import FacilityInteractor
from apps.ops.app.use_cases.healthcare_interactor import HealthcareInteractor
from apps.ops.dependencies.ops_dependencies import get_facility_use_case, get_healthcare_use_case
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

PASSWORD = "correct-horse-battery"
CLIENT = ("198.51.100.20", 50000)


def _ollama_transport(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/tags":
        return httpx.Response(200, json={"models": [{"name": "gemma4:12b", "size": 8_000_000_000}]})
    return httpx.Response(200, json={"models": [{"name": "gemma4:12b"}]})


class _EchoProbe(ProbePort):
    def run(self, message: str) -> ProbeResultDto:
        return ProbeResultDto(kind="llm", ok=True, latency_ms=12, model="fake", output=message)


class _OneGpu(GpuMetricsPort):
    def read(self) -> list[GpuDto]:
        return [GpuDto(index=0, name="RTX", memory_used_mb=1024, memory_total_mb=16384, utilization_percent=7, temperature_c=40)]


def _fake_proc(tmp_path: Path) -> Path:
    (tmp_path / "meminfo").write_text("MemTotal: 16000 kB\nMemAvailable: 4000 kB\nSwapTotal: 2000 kB\nSwapFree: 500 kB\n")
    (tmp_path / "loadavg").write_text("0.50 0.40 0.30 1/200 999\n")
    (tmp_path / "uptime").write_text("3600.12 7000.00\n")
    (tmp_path / "stat").write_text("cpu 100 0 100 700 100 0 0 0 0 0\n")
    return tmp_path


@pytest.fixture
def ollama() -> OllamaStatusGateway:
    return OllamaStatusGateway(transport=httpx.MockTransport(_ollama_transport))


@pytest.fixture(autouse=True)
def fakes(tmp_path: Path, ollama: OllamaStatusGateway):
    with session_scope() as session:
        session.execute(text("truncate access_event, ip_block, admin_session, admin_user restart identity cascade"))
    get_admin_user_use_case().upsert("ops", PASSWORD, "operator")
    get_admin_user_use_case().upsert("viewer", PASSWORD, "viewer")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "news-poller.log").write_text("ok\n")
    app.dependency_overrides[get_healthcare_use_case] = lambda: HealthcareInteractor(
        ollama=ollama, chain=LlmChainGateway(), usage=LlmUsageGateway(), rag=RagStatsGateway(),
        probes={"llm": _EchoProbe(), "rag": _EchoProbe()},
    )
    app.dependency_overrides[get_facility_use_case] = lambda: FacilityInteractor(
        host=ProcHostGateway(proc_root=_fake_proc(tmp_path)), gpus=_OneGpu(), database=PostgresStatusGateway(),
        ollama=ollama, logs=CollectorLogGateway(logs_dir=tmp_path / "logs"),
    )
    yield
    app.dependency_overrides.clear()


def _client(username: str) -> TestClient:
    client = TestClient(app, client=CLIENT)
    assert client.post("/admin/auth/login", json={"username": username, "password": PASSWORD}).status_code == 200
    return client


def test_meminfo는_kB를_바이트로_바꾼다():
    assert parse_meminfo("MemTotal: 2 kB\nHugePages_Total: 3\n") == {"MemTotal": 2048, "HugePages_Total": 3}


def test_CPU_사용률은_두_표본의_비유휴_비율이다():
    assert cpu_busy_percent([100, 0, 100, 700, 100], [200, 0, 200, 800, 100]) == 66.7
    assert cpu_busy_percent([1, 1, 1, 1], [1, 1, 1, 1]) is None


def test_nvidia_smi_출력을_GPU_목록으로_읽는다():
    gpus = parse_nvidia_smi("0, NVIDIA GeForce RTX 4090, 2048, 24564, 13, 45\n1, A100, 10, 40960, [N/A], [N/A]\n")
    assert (gpus[0].name, gpus[0].memory_total_mb, gpus[0].temperature_c) == ("NVIDIA GeForce RTX 4090", 24564, 45)
    assert (gpus[1].utilization_percent, gpus[1].temperature_c) == (0, None)


def test_Ollama가_꺼져_있어도_예외_없이_연결_안_됨으로_돌려준다():
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    status = OllamaStatusGateway(transport=httpx.MockTransport(refuse)).read()
    assert (status.reachable, status.error) == (False, "ConnectError")


def test_카탈로그에_없는_테이블_조회는_거절한다():
    with pytest.raises(ValueError):
        PostgresStatusGateway().table_stats("admin_user", "password_hash")


def test_myself_배선_2종이_200을_반환한다():
    client = TestClient(app)
    assert client.get("/admin/healthcare/myself").status_code == 200
    assert client.get("/admin/facility/myself").json()["name"] == "myself"


def test_비로그인은_스냅샷에_401():
    client = TestClient(app)
    assert client.get("/admin/healthcare/snapshot").status_code == 401
    assert client.get("/admin/facility/snapshot").status_code == 401


def test_헬스케어_스냅샷은_LLM_경로와_필수_모델과_RAG_집계를_담는다():
    body = _client("viewer").get("/admin/healthcare/snapshot").json()
    routes = {r["provider"]: r for r in body["llm_routes"]}
    assert routes["ollama"]["available"] is True  # 가짜 Ollama에 gemma4:12b 설치됨
    required = {m["name"]: m for m in body["required_models"]}
    assert required["gemma4:12b"]["loaded"] is True
    assert required["qwen3-embedding:4b"]["installed"] is False
    assert body["usage_24h"]["window_hours"] == 24
    assert isinstance(body["rag"]["total_chunks"], int)


def test_프로브는_운영_관리자만_실행한다():
    payload = {"kind": "llm", "message": "안녕"}
    assert _client("viewer").post("/admin/healthcare/probe", json=payload).status_code == 403
    response = _client("ops").post("/admin/healthcare/probe", json=payload)
    assert response.status_code == 200
    assert response.json()["output"] == "안녕"


def test_모르는_프로브_종류는_422():
    response = _client("ops").post("/admin/healthcare/probe", json={"kind": "sql", "message": "x"})
    assert response.status_code == 422


def test_설비_스냅샷은_호스트_GPU_DB_수집기_상태를_담는다():
    body = _client("viewer").get("/admin/facility/snapshot").json()
    host = body["host"]
    assert (host["memory_total_bytes"], host["swap_used_bytes"], host["uptime_seconds"]) == (16000 * 1024, 1500 * 1024, 3600)
    assert host["load_avg"] == [0.5, 0.4, 0.3]
    assert body["gpus"][0]["name"] == "RTX"
    assert {s["name"]: s["ok"] for s in body["services"]} == {"postgres": True, "ollama": True}
    assert body["database"]["alembic_revision"]
    collectors = {c["key"]: c for c in body["collectors"]}
    assert collectors["news-poller"]["status"] == "ok"
    assert collectors["store-collector"]["status"] == "missing"
    assert collectors["store-collector"]["rows"] is not None


def test_로그_수정_시각을_UTC로_돌려준다(tmp_path: Path):
    (tmp_path / "a.log").write_text("x")
    last = CollectorLogGateway(logs_dir=tmp_path).last_modified("a.log")
    assert last is not None and last.tzinfo is UTC and (datetime.now(UTC) - last).total_seconds() < 60
    assert CollectorLogGateway(logs_dir=tmp_path).last_modified("none.log") is None
