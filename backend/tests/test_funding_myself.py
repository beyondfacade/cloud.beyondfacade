"""funding BC 배선 검증 — GET /funding/myself (CLAUDE.md §12 라우터 최초 검증 규칙)."""

from fastapi.testclient import TestClient

from main import app


def test_funding_myself_wiring_returns_200():
    client = TestClient(app)
    response = client.get("/funding/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["program_id"] == "myself"
    assert body["title"]
    assert body["url"]
