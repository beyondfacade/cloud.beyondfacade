"""헬스체크 — liveness(/health)와 readiness(/health/ready, DB 연결 확인)를 나눈다 (k8s 롤링 배포용)."""

from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

import main
from main import app


def test_DB에_붙으면_ready는_200():
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_DB에_못_붙으면_ready는_503(monkeypatch):
    @contextmanager
    def broken_session():
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        yield

    monkeypatch.setattr(main, "session_scope", broken_session)
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DB_UNAVAILABLE"
