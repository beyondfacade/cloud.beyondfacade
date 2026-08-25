"""store BC 배선 검증 — GET /stores/myself (CLAUDE.md §12)."""

from fastapi.testclient import TestClient

from main import app


def test_store_myself_wiring_returns_200():
    client = TestClient(app)
    response = client.get("/stores/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["store_id"] == "myself"
    assert body["name"]
