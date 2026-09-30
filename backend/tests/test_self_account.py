"""내 계정 관리 — 관리자도 남의 등급·비밀번호는 못 바꾸고, 누구나 자기 계정명·비밀번호는 바꾼다 (실제 테스트 DB)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

OPS_IP = ("198.51.100.60", 50000)
VIEWER_IP = ("198.51.100.61", 50000)
PASSWORD = "correct-horse-battery"
NEW_PASSWORD = "brand-new-staple-battery"


@pytest.fixture(autouse=True)
def clean_admin_tables():
    with session_scope() as session:
        session.execute(
            text("truncate access_event, ip_block, admin_session, admin_audit, admin_user restart identity cascade")
        )
    use_case = get_admin_user_use_case()
    use_case.upsert("ops", PASSWORD, "operator")
    use_case.upsert("viewer", PASSWORD, "viewer")


def _client(username: str, ip=VIEWER_IP, password: str = PASSWORD) -> TestClient:
    client = TestClient(app, client=ip)
    assert client.post("/admin/auth/login", json={"username": username, "password": password}).status_code == 200
    return client


def _audit() -> list[tuple[str, str, str]]:
    with session_scope() as session:
        rows = session.execute(text("select action, target, detail from admin_audit order by id")).all()
    return [tuple(row) for row in rows]


# ── 남의 계정은 못 바꾼다 ─────────────────────────────────


def test_관리자도_남의_등급은_바꿀_수_없다():
    ops = _client("ops", ip=OPS_IP)
    response = ops.patch("/admin/users/viewer/role", json={"role": "operator"})
    assert response.status_code in (404, 405)
    assert _client("viewer").get("/admin/auth/me").json()["role"] == "viewer"


def test_관리자도_남의_비밀번호는_재설정할_수_없다():
    ops = _client("ops", ip=OPS_IP)
    response = ops.put("/admin/users/viewer/password", json={"password": NEW_PASSWORD})
    assert response.status_code in (404, 405)
    _client("viewer")


def test_관리자도_화면에서_계정을_만들_수는_없다():
    ops = _client("ops", ip=OPS_IP)
    response = ops.post("/admin/users", json={"username": "new.one", "role": "operator", "password": NEW_PASSWORD})
    assert response.status_code == 405


# ── 내 계정명 변경 ───────────────────────────────────────


def test_내_계정명을_바꾸면_세션은_그대로이고_새_이름으로만_로그인한다():
    me = _client("viewer")
    response = me.patch("/admin/auth/username", json={"username": "viewer.kim"})
    assert response.status_code == 200
    assert response.json() == {"username": "viewer.kim", "role": "viewer", "can_operate": False}
    assert me.get("/admin/auth/me").json()["username"] == "viewer.kim"
    _client("viewer.kim")
    stale = TestClient(app, client=VIEWER_IP).post("/admin/auth/login", json={"username": "viewer", "password": PASSWORD})
    assert stale.status_code == 401
    assert ("username.change", "viewer.kim", "viewer → viewer.kim") in _audit()


def test_관리자도_자기_계정명을_바꿀_수_있다():
    ops = _client("ops", ip=OPS_IP)
    assert ops.patch("/admin/auth/username", json={"username": "ops.lead"}).json()["can_operate"] is True


@pytest.mark.parametrize(
    ("username", "status", "code"),
    [("ops", 409, "USERNAME_TAKEN"), ("Bad Name", 400, "INVALID_USERNAME"), ("ab", 400, "INVALID_USERNAME")],
)
def test_계정명_규칙을_어기거나_이미_있으면_거절한다(username, status, code):
    response = _client("viewer").patch("/admin/auth/username", json={"username": username})
    assert (response.status_code, response.json()["error"]["code"]) == (status, code)


def test_지금과_같은_계정명이면_아무것도_바꾸지_않는다():
    response = _client("viewer").patch("/admin/auth/username", json={"username": "viewer"})
    assert response.json()["username"] == "viewer"
    assert not [row for row in _audit() if row[0] == "username.change"]


def test_계정명_변경은_로그인이_필요하다():
    assert TestClient(app).patch("/admin/auth/username", json={"username": "someone"}).status_code == 401


# ── 내 비밀번호 ─────────────────────────────────────────


def test_비밀번호가_있는_계정은_현재_비밀번호를_비우면_거절한다():
    response = _client("viewer").post("/admin/auth/password", json={"new_password": NEW_PASSWORD})
    assert (response.status_code, response.json()["error"]["code"]) == (400, "WRONG_PASSWORD")
