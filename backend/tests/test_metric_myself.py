"""metric BC 배선 검증 — GET /metrics/myself (CLAUDE.md §12)."""

from fastapi.testclient import TestClient

from main import app


def test_metric_myself_wiring_returns_200():
    client = TestClient(app)
    response = client.get("/metrics/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["region_code"] == "myself"
    assert body["industry_id"]
