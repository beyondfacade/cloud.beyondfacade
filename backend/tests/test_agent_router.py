"""agent 분석 라우터 검증 — POST·SSE 프레임·404·myself 배선 (Fake AnalysisUseCase)."""

from collections.abc import Iterator
from uuid import UUID

from fastapi.testclient import TestClient

from apps.agent.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.agent.dependencies.analysis_dependencies import get_analysis_use_case
from apps.agent.domain.entities.agent_event_entity import AgentEvent
from main import app

_FIXED_EVENTS = (
    AgentEvent("agent_status", {"agent": "orchestrator", "status": "running"}),
    AgentEvent("report_delta", {"section": "verdict", "markdown": "### 종합 판정\n\n테스트"}),
    AgentEvent(
        "report_done",
        {"report_id": "will-be-overridden", "citations": [{"title": "t", "url": "", "grade": "fact"}]},
    ),
)


class FakeAnalysisUseCase(AnalysisUseCase):
    def myself(self) -> dict:
        return {
            "analysis_id": "myself",
            "region_code": "myself",
            "industry": "myself",
            "model": "gemma3",
        }

    def run(self, region: str, industry: str, question: str | None) -> Iterator[AgentEvent]:
        assert region and industry  # 라우터가 파라미터를 넘기는지 확인
        yield from _FIXED_EVENTS


def setup_function() -> None:
    app.dependency_overrides[get_analysis_use_case] = lambda: FakeAnalysisUseCase()


def teardown_function() -> None:
    app.dependency_overrides.clear()
    # 프로세스 수명 pending 잔여 제거
    from apps.agent.adapter.inbound.api.v1 import analysis_router

    analysis_router._PENDING.clear()


def test_analysis_myself_wiring_returns_200():
    response = TestClient(app).get("/analysis/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == "myself"
    assert body["model"]


def test_post_analysis_returns_uuid():
    response = TestClient(app).post(
        "/analysis",
        json={"region": "1168064000", "industry": "cafe"},
    )
    assert response.status_code == 200
    analysis_id = response.json()["analysis_id"]
    UUID(analysis_id)  # uuid4 형식


def test_get_events_streams_sse_frames_in_order():
    client = TestClient(app)
    analysis_id = client.post(
        "/analysis",
        json={"region": "1168064000", "industry": "cafe", "question": "괜찮을까요?"},
    ).json()["analysis_id"]

    response = client.get(f"/analysis/{analysis_id}/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text

    assert "event: agent_status\n" in body
    assert "event: report_delta\n" in body
    assert "event: report_done\n" in body
    assert "data: " in body

    # 프레임 순서 — agent_status → report_delta → report_done
    pos_status = body.index("event: agent_status\n")
    pos_delta = body.index("event: report_delta\n")
    pos_done = body.index("event: report_done\n")
    assert pos_status < pos_delta < pos_done


def test_unknown_analysis_id_returns_404_body():
    response = TestClient(app).get("/analysis/does-not-exist/events")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "ANALYSIS_NOT_FOUND"
    assert body["error"]["message"]
