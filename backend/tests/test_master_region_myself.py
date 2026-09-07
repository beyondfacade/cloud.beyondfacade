"""region BC 배선 검증 — GET /regions/myself (CLAUDE.md §12)."""

from fastapi.testclient import TestClient

from main import app


def test_region_myself_wiring_returns_200():
    client = TestClient(app)
    response = client.get("/regions/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["region_code"] == "myself"
    assert body["name"]
