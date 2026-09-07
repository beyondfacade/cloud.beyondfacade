"""shock BC 배선 검증 — GET /shocks/myself (CLAUDE.md §12 라우터 최초 검증 규칙)."""

from fastapi.testclient import TestClient

from main import app


def test_shock_myself_wiring_returns_200():
    client = TestClient(app)
    response = client.get("/shocks/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["event_id"] == "myself"
    assert body["name"]
    assert body["layer"]


def test_shock_list_rejects_invalid_limit():
    client = TestClient(app)
    response = client.get("/shocks", params={"limit": 0})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_LIMIT"
