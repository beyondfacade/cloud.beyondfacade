"""agent 분석 라우터 검증 — POST·SSE 프레임·404·myself 배선 (Fake AnalysisUseCase)."""

import json
from collections.abc import Iterator
from datetime import datetime
from uuid import UUID

from fastapi.testclient import TestClient

from apps.agent.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.agent.dependencies.analysis_dependencies import get_analysis_use_case
from apps.agent.domain.entities.agent_event_entity import AgentEvent
from main import app

from apps.agent.app.use_cases.report_facts import FACTS_KEYS

_FACTS = {key: {"available": False, "reason": "테스트"} for key in FACTS_KEYS}
_FACTS["region"] = {"code": "1168064000", "name": "역삼1동", "industry_id": "cafe", "industry_name": "카페"}
_FACTS["budget"] = None

_FIXED_EVENTS = (
    AgentEvent("agent_status", {"agent": "orchestrator", "status": "running"}),
    AgentEvent("facts", {"facts": _FACTS}),
    AgentEvent("report_delta", {"section": "verdict", "markdown": "### 판정\n\n테스트"}),
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


class _NullRepository:
    """SSE 종료 시 영속화 경로가 실제 DB를 건드리지 않게 하는 Fake."""

    def save_report(self, **kwargs) -> None:
        return None


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


def test_facts_프레임이_열두_키를_그대로_싣는다():
    """프론트는 이 한 프레임으로 시각 자료를 전부 그린다 — 키가 빠지면 그림이 사라진다 (설계서 §5)."""
    client = TestClient(app)
    analysis_id = client.post(
        "/analysis",
        json={"region": "1168064000", "industry": "cafe"},
    ).json()["analysis_id"]

    body = client.get(f"/analysis/{analysis_id}/events").text

    frame = [line for line in body.splitlines() if line.startswith("data: ")][1]
    payload = json.loads(frame[len("data: ") :])
    assert payload["type"] == "facts"
    # 프론트 계약은 중첩이다 — {type:"facts", facts:{…12키}} (설계서 §4-1)
    assert set(payload) == {"type", "facts"}
    assert set(payload["facts"]) == set(FACTS_KEYS)
    assert payload["facts"]["region"]["name"] == "역삼1동"


def test_직렬화할_수_없는_값이_섞여도_프레임이_끊기지_않는다():
    """SSE 프레임 하나가 TypeError로 죽으면 스트림 전체가 잘린다 — 문자열로라도 내보낸다."""
    from apps.agent.adapter.inbound.api.v1.analysis_router import _sse_frame

    frame = _sse_frame(AgentEvent("facts", {"facts": {"computed_at": datetime(2026, 9, 29)}}))

    assert json.loads(frame.split("data: ")[1])["facts"]["computed_at"] == "2026-09-29 00:00:00"


def test_unknown_analysis_id_returns_404_body():
    response = TestClient(app).get("/analysis/does-not-exist/events")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "ANALYSIS_NOT_FOUND"
    assert body["error"]["message"]


def test_예산을_받으면_pending에_실린다():
    """budget은 finance 도구 기본값으로 배선에 넘어간다 (설계서 §5-2)."""
    from apps.agent.adapter.inbound.api.v1 import analysis_router

    analysis_id = TestClient(app).post(
        "/analysis",
        json={"region": "1168064000", "industry": "cafe", "budget": 50_000_000},
    ).json()["analysis_id"]

    assert analysis_router._PENDING[analysis_id]["budget"] == 50_000_000


def test_예산_없는_기존_요청도_그대로_받는다():
    """FE 컷오버 전 요청 호환 — budget은 선택이고 없으면 None이다."""
    from apps.agent.adapter.inbound.api.v1 import analysis_router

    response = TestClient(app).post(
        "/analysis",
        json={"region": "1168064000", "industry": "cafe"},
    )

    assert response.status_code == 200
    assert analysis_router._PENDING[response.json()["analysis_id"]]["budget"] is None


def test_음수_예산은_422로_거절된다():
    """예산은 0원 이상만 받는다 — 음수는 finance 도구 기본값이 될 수 없다."""
    response = TestClient(app).post(
        "/analysis",
        json={"region": "1168064000", "industry": "cafe", "budget": -1},
    )

    assert response.status_code == 422


def test_SSE_배선은_pending_예산을_UseCase_생성에_넘긴다(monkeypatch):
    """budget이 build_analysis_use_case까지 실제로 흘러야 finance 도구 기본값이 된다 (설계서 §5-2)."""
    from apps.agent.adapter.inbound.api.v1 import analysis_router
    from apps.agent.dependencies.analysis_dependencies import get_analysis_repository

    app.dependency_overrides.clear()  # 오버라이드가 있으면 배선이 build_analysis_use_case를 건너뛴다
    app.dependency_overrides[get_analysis_repository] = lambda: _NullRepository()
    captured: dict = {}

    def fake_build(model: str = "hybrid", budget: int | None = None) -> AnalysisUseCase:
        captured["model"], captured["budget"] = model, budget
        return FakeAnalysisUseCase()

    monkeypatch.setattr(analysis_router, "build_analysis_use_case", fake_build)

    client = TestClient(app)
    analysis_id = client.post(
        "/analysis",
        json={"region": "1168064000", "industry": "cafe", "budget": 50_000_000},
    ).json()["analysis_id"]
    client.get(f"/analysis/{analysis_id}/events")

    assert captured == {"model": "hybrid", "budget": 50_000_000}


def test_저장되는_report_md는_조각을_섹션별로_이어_붙인_글이다(monkeypatch):
    """report_delta가 조각 단위가 됐다 — 조각마다 빈 줄을 넣으면 저장본이 글이 아니게 된다."""
    from apps.agent.adapter.inbound.api.v1 import analysis_router
    from apps.agent.dependencies.analysis_dependencies import get_analysis_repository

    saved: dict = {}

    class _CapturingRepository:
        def save_report(self, **kwargs) -> None:
            saved.update(kwargs)

    class _ChunkedUseCase(FakeAnalysisUseCase):
        def run(self, region, industry, question):
            yield AgentEvent("report_delta", {"section": "verdict", "markdown": "🔴 "})
            yield AgentEvent("report_delta", {"section": "verdict", "markdown": "비추천."})
            yield AgentEvent("report_delta", {"section": "reasons", "markdown": "폐업률이 높다."})
            yield AgentEvent("report_done", {"report_id": "x", "citations": []})

    app.dependency_overrides.clear()  # 오버라이드가 있으면 영속화 경로를 건너뛴다
    app.dependency_overrides[get_analysis_repository] = lambda: _CapturingRepository()
    monkeypatch.setattr(analysis_router, "build_analysis_use_case", lambda *a, **k: _ChunkedUseCase())

    client = TestClient(app)
    analysis_id = client.post("/analysis", json={"region": "1168064000", "industry": "cafe"}).json()[
        "analysis_id"
    ]
    client.get(f"/analysis/{analysis_id}/events")

    assert saved["report_md"] == "🔴 비추천.\n\n폐업률이 높다."
