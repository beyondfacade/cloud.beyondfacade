"""news BC 배선 검증 — GET /news/myself (CLAUDE.md §12 라우터 최초 검증 규칙)."""

from fastapi.testclient import TestClient

from main import app


def test_news_myself_wiring_returns_200():
    client = TestClient(app)
    response = client.get("/news/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["article_id"] == "myself"
    assert body["title"]
