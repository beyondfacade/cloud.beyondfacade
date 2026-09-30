"""인사팀 — 관리자 계정 목록·생성·역할·정지·비밀번호·세션 API (실제 테스트 DB)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

OPS_IP = ("198.51.100.20", 50000)
VIEWER_IP = ("198.51.100.21", 50000)
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


def _client(username: str, ip=OPS_IP, password: str = PASSWORD) -> TestClient:
    client = TestClient(app, client=ip)
    assert client.post("/admin/auth/login", json={"username": username, "password": password}).status_code == 200
    return client


def _actions() -> list[str]:
    with session_scope() as session:
        return session.execute(text("select action from admin_audit order by id")).scalars().all()


def test_myself_배선이_200을_반환한다():
    assert TestClient(app).get("/admin/users/myself").json()["username"] == "myself"


def test_계정_목록은_로그인이_필요하다():
    assert TestClient(app).get("/admin/users").status_code == 401


def test_계정_목록은_활성_세션_수와_마지막_로그인을_담는다():
    ops = _client("ops")
    _client("ops", ip=("198.51.100.30", 50000))
    items = {item["username"]: item for item in ops.get("/admin/users").json()["items"]}
    assert items["ops"]["active_sessions"] == 2
    assert items["ops"]["last_login_at"] is not None
    assert items["viewer"]["active_sessions"] == 0
    assert items["viewer"]["role"] == "viewer"
    assert items["viewer"]["is_active"] is True
    assert "password_hash" not in items["ops"]


def test_계정_목록은_검색어_역할_상태로_거른다():
    ops = _client("ops")
    ops.post("/admin/users", json={"username": "ops.lee", "role": "operator", "password": NEW_PASSWORD})
    ops.patch("/admin/users/viewer/status", json={"active": False})
    names = lambda params: [item["username"] for item in ops.get("/admin/users", params=params).json()["items"]]  # noqa: E731
    assert names({"q": "OPS"}) == ["ops", "ops.lee"]
    assert names({"role": "viewer"}) == ["viewer"]
    assert names({"status": "suspended"}) == ["viewer"]
    assert names({"status": "active", "role": "operator"}) == ["ops", "ops.lee"]


def test_조회_관리자도_목록은_보지만_계정을_만들_수는_없다():
    viewer = _client("viewer", ip=VIEWER_IP)
    assert viewer.get("/admin/users").status_code == 200
    response = viewer.post("/admin/users", json={"username": "new.one", "role": "viewer", "password": NEW_PASSWORD})
    assert response.status_code == 403


def test_운영_관리자는_계정을_만들고_감사에_남는다():
    ops = _client("ops")
    response = ops.post("/admin/users", json={"username": "new.one", "role": "viewer", "password": NEW_PASSWORD})
    assert response.status_code == 201
    assert response.json()["username"] == "new.one"
    assert _client("new.one", ip=VIEWER_IP, password=NEW_PASSWORD).get("/admin/auth/me").json()["role"] == "viewer"
    assert "user.create" in _actions()


def test_계정_생성은_중복_이름_잘못된_이름_짧은_비밀번호를_거절한다():
    ops = _client("ops")
    taken = ops.post("/admin/users", json={"username": "viewer", "role": "viewer", "password": NEW_PASSWORD})
    assert (taken.status_code, taken.json()["error"]["code"]) == (409, "USERNAME_TAKEN")
    bad = ops.post("/admin/users", json={"username": "Bad Name", "role": "viewer", "password": NEW_PASSWORD})
    assert (bad.status_code, bad.json()["error"]["code"]) == (400, "INVALID_USERNAME")
    weak = ops.post("/admin/users", json={"username": "short.pw", "role": "viewer", "password": "short"})
    assert (weak.status_code, weak.json()["error"]["code"]) == (400, "WEAK_PASSWORD")


def test_역할을_바꾸면_다음_요청부터_권한이_바뀐다():
    ops = _client("ops")
    viewer = _client("viewer", ip=VIEWER_IP)
    response = ops.patch("/admin/users/viewer/role", json={"role": "operator"})
    assert response.json()["role"] == "operator"
    assert viewer.get("/admin/auth/me").json()["can_operate"] is True
    assert "user.role" in _actions()


def test_자기_역할과_상태는_바꿀_수_없다():
    ops = _client("ops")
    ops.post("/admin/users", json={"username": "ops2", "role": "operator", "password": NEW_PASSWORD})
    role = ops.patch("/admin/users/ops/role", json={"role": "viewer"})
    assert (role.status_code, role.json()["error"]["code"]) == (400, "SELF_CHANGE")
    status = ops.patch("/admin/users/ops/status", json={"active": False})
    assert status.json()["error"]["code"] == "SELF_CHANGE"


def test_강등된_운영자는_곧바로_운영_권한을_잃는다():
    ops = _client("ops")
    ops.post("/admin/users", json={"username": "ops2", "role": "operator", "password": NEW_PASSWORD})
    ops2 = _client("ops2", ip=VIEWER_IP, password=NEW_PASSWORD)
    assert ops2.patch("/admin/users/ops/role", json={"role": "viewer"}).status_code == 200
    assert ops.patch("/admin/users/ops2/role", json={"role": "viewer"}).status_code == 403


def test_정지하면_그_계정의_세션이_끊기고_로그인도_막힌다():
    ops = _client("ops")
    viewer = _client("viewer", ip=VIEWER_IP)
    response = ops.patch("/admin/users/viewer/status", json={"active": False})
    assert response.json()["is_active"] is False
    assert viewer.get("/admin/auth/me").status_code == 401
    relogin = TestClient(app, client=VIEWER_IP).post(
        "/admin/auth/login", json={"username": "viewer", "password": PASSWORD}
    )
    assert relogin.status_code == 401
    ops.patch("/admin/users/viewer/status", json={"active": True})
    assert _client("viewer", ip=VIEWER_IP).get("/admin/auth/me").status_code == 200
    assert _actions()[-2:] == ["user.suspend", "user.reactivate"]


def test_없는_계정은_404다():
    ops = _client("ops")
    response = ops.patch("/admin/users/ghost/role", json={"role": "viewer"})
    assert (response.status_code, response.json()["error"]["code"]) == (404, "ADMIN_USER_NOT_FOUND")


def test_비밀번호를_재설정하면_기존_세션이_끊기고_새_비밀번호로만_들어온다():
    ops = _client("ops")
    viewer = _client("viewer", ip=VIEWER_IP)
    assert ops.put("/admin/users/viewer/password", json={"password": NEW_PASSWORD}).status_code == 204
    assert viewer.get("/admin/auth/me").status_code == 401
    _client("viewer", ip=VIEWER_IP, password=NEW_PASSWORD)
    assert "user.password_reset" in _actions()


def test_세션_목록은_본인_또는_운영자만_보고_현재_세션을_표시한다():
    viewer = _client("viewer", ip=VIEWER_IP)
    mine = viewer.get("/admin/users/viewer/sessions").json()["items"]
    assert len(mine) == 1
    assert mine[0]["current"] is True
    assert mine[0]["ip"] == "198.51.100.21"
    assert len(mine[0]["id"]) == 12
    assert viewer.get("/admin/users/ops/sessions").status_code == 403
    ops = _client("ops")
    theirs = ops.get("/admin/users/viewer/sessions").json()["items"]
    assert theirs[0]["current"] is False


def test_내_세션을_모두_끊어도_지금_세션은_남는다():
    viewer = _client("viewer", ip=VIEWER_IP)
    other = _client("viewer", ip=("198.51.100.40", 50000))
    response = viewer.delete("/admin/users/viewer/sessions")
    assert response.json()["revoked"] == 1
    assert viewer.get("/admin/auth/me").status_code == 200
    assert other.get("/admin/auth/me").status_code == 401


def test_운영자가_남의_세션을_끊으면_전부_끊긴다():
    ops = _client("ops")
    viewer = _client("viewer", ip=VIEWER_IP)
    assert ops.delete("/admin/users/viewer/sessions").json()["revoked"] == 1
    assert viewer.get("/admin/auth/me").status_code == 401
    assert "user.sessions_revoke" in _actions()


def test_내_비밀번호_변경은_현재_비밀번호를_확인하고_다른_세션을_끊는다():
    me = _client("viewer", ip=VIEWER_IP)
    other = _client("viewer", ip=("198.51.100.40", 50000))
    wrong = me.post("/admin/auth/password", json={"current_password": "not-my-password", "new_password": NEW_PASSWORD})
    assert (wrong.status_code, wrong.json()["error"]["code"]) == (400, "WRONG_PASSWORD")
    ok = me.post("/admin/auth/password", json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
    assert ok.status_code == 204
    assert me.get("/admin/auth/me").status_code == 200
    assert other.get("/admin/auth/me").status_code == 401
    _client("viewer", ip=VIEWER_IP, password=NEW_PASSWORD)
    assert "password.change" in _actions()


def test_내_비밀번호_변경도_12자_규칙을_지킨다():
    me = _client("viewer", ip=VIEWER_IP)
    weak = me.post("/admin/auth/password", json={"current_password": PASSWORD, "new_password": "short"})
    assert weak.json()["error"]["code"] == "WEAK_PASSWORD"
