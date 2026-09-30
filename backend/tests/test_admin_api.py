"""관리자 인증·권한 가드·보안 미들웨어·보안감사 API — 실제 테스트 DB를 거친다."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.admin.adapter.inbound.api.client_ip import resolve_client_ip
from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from apps.admin.domain.entities.access_event_entity import AccessEventKind
from apps.admin.domain.services.response_classifier import response_event_kind
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

ATTACKER = ("203.0.113.10", 50000)
OPERATOR_IP = ("198.51.100.20", 50000)
PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def clean_admin_tables():
    with session_scope() as session:
        session.execute(text("truncate access_event, ip_block, admin_session, admin_user restart identity cascade"))
    use_case = get_admin_user_use_case()
    use_case.upsert("ops", PASSWORD, "operator")
    use_case.upsert("viewer", PASSWORD, "viewer")


def _login(client: TestClient, username: str, password: str = PASSWORD):
    return client.post("/admin/auth/login", json={"username": username, "password": password})


def _count_events(kind: str) -> int:
    with session_scope() as session:
        return session.execute(text("select count(*) from access_event where kind = :k"), {"k": kind}).scalar_one()


def test_클라이언트_IP는_사설망_프록시가_붙인_XFF_마지막_값을_믿는다():
    assert resolve_client_ip("127.0.0.1", "1.1.1.1, 203.0.113.10") == "203.0.113.10"
    assert resolve_client_ip("172.18.0.3", "203.0.113.10") == "203.0.113.10"


def test_공인_IP_피어의_XFF는_위조일_수_있어_무시한다():
    assert resolve_client_ip("203.0.113.10", "10.0.0.1") == "203.0.113.10"
    assert resolve_client_ip("127.0.0.1", "not-an-ip") == "127.0.0.1"


def test_응답_분류_5xx와_스캐너_경로만_보안_이벤트다():
    assert response_event_kind(500, "/stores") == AccessEventKind.SERVER_ERROR
    assert response_event_kind(404, "/.env") == AccessEventKind.SCANNER_PROBE
    assert response_event_kind(404, "/stores/x") is None
    assert response_event_kind(200, "/wp-login.php") is None


def test_myself_배선_3종이_200을_반환한다():
    client = TestClient(app)
    assert client.get("/admin/auth/myself").json()["username"] == "myself"
    assert client.get("/admin/security/myself").status_code == 200
    assert client.get("/admin/security/ip-blocks/myself").json()["ip"] == "192.0.2.1"


def test_로그인하면_httpOnly_쿠키가_생기고_me가_역할을_돌려준다():
    client = TestClient(app, client=OPERATOR_IP)
    response = _login(client, "ops")
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "token" not in response.json()
    me = client.get("/admin/auth/me").json()
    assert (me["username"], me["role"], me["can_operate"]) == ("ops", "operator", True)
    assert _count_events("login_succeeded") == 1


def test_틀린_비밀번호는_401이고_실패_이벤트가_남는다():
    client = TestClient(app, client=ATTACKER)
    response = _login(client, "ops", "wrong-password")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert _count_events("login_failed") == 1


def test_같은_IP_실패_10회_뒤에는_맞는_비밀번호도_429():
    client = TestClient(app, client=ATTACKER)
    for _ in range(10):
        _login(client, "ops", "wrong-password")
    response = _login(client, "ops")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"


def test_로그아웃하면_세션이_무효가_된다():
    client = TestClient(app, client=OPERATOR_IP)
    _login(client, "ops")
    assert client.post("/admin/auth/logout").status_code == 204
    assert client.get("/admin/auth/me").status_code == 401


def test_비로그인은_보안_개요에_401():
    response = TestClient(app).get("/admin/security/overview")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_조회_관리자는_개요는_보지만_IP_차단은_403():
    client = TestClient(app, client=OPERATOR_IP)
    _login(client, "viewer")
    assert client.get("/admin/security/overview").status_code == 200
    response = client.post("/admin/security/ip-blocks", json={"ip": "203.0.113.10", "reason": "x"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_운영_관리자가_차단하면_그_IP는_관리자_경로에서_403이고_해제하면_풀린다():
    operator = TestClient(app, client=OPERATOR_IP)
    _login(operator, "ops")
    created = operator.post(
        "/admin/security/ip-blocks", json={"ip": "203.0.113.10", "reason": "무차별 대입", "ttl_minutes": 60}
    )
    assert created.status_code == 201
    assert created.json()["created_by"] == "ops"
    assert [b["ip"] for b in operator.get("/admin/security/ip-blocks").json()] == ["203.0.113.10"]

    attacker = TestClient(app, client=ATTACKER)
    blocked = _login(attacker, "ops")
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "IP_BLOCKED"
    assert attacker.get("/health").status_code == 200  # 공개 경로는 막지 않는다
    assert _count_events("blocked_request") == 1

    assert operator.delete("/admin/security/ip-blocks/203.0.113.10").status_code == 204
    assert _login(attacker, "ops").status_code == 200


def test_형식이_틀린_IP와_자기_IP_차단은_400():
    client = TestClient(app, client=OPERATOR_IP)
    _login(client, "ops")
    bad = client.post("/admin/security/ip-blocks", json={"ip": "999.1.1.1", "reason": "x"})
    assert bad.json()["error"]["code"] == "INVALID_IP"
    own = client.post("/admin/security/ip-blocks", json={"ip": OPERATOR_IP[0], "reason": "x"})
    assert (own.status_code, own.json()["error"]["code"]) == (400, "SELF_BLOCK")


def test_없는_IP_해제는_404():
    client = TestClient(app, client=OPERATOR_IP)
    _login(client, "ops")
    response = client.delete("/admin/security/ip-blocks/192.0.2.99")
    assert (response.status_code, response.json()["error"]["code"]) == (404, "IP_BLOCK_NOT_FOUND")


def test_스캐너_탐색이_기록되고_보안_개요의_알림이_된다():
    attacker = TestClient(app, client=ATTACKER)
    for path in ("/.env", "/wp-login.php", "/.git/config"):
        assert attacker.get(path).status_code == 404
    for _ in range(5):
        _login(attacker, "ops", "wrong-password")

    client = TestClient(app, client=OPERATOR_IP)
    _login(client, "ops")
    body = client.get("/admin/security/overview").json()
    assert body["summary"]["scanner_probes_24h"] == 3
    assert body["summary"]["failed_logins_24h"] == 5
    assert {(a["rule"], a["ip"]) for a in body["alerts"]} == {
        ("scanner_probe", ATTACKER[0]),
        ("brute_force_login", ATTACKER[0]),
    }
    assert body["recent_events"][0]["kind"] == "login_succeeded"
