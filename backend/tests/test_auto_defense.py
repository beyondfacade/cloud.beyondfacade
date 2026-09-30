"""자동 방어 — 로그인 실패·스캐너 탐색이 쌓인 IP를 자동 차단하고, 관리자가 켜고 끈다 (실제 테스트 DB)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.admin.adapter.outbound.repositories.ip_block_repository import SqlAlchemyIpBlockRepository
from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from apps.admin.domain.entities.ip_block_entity import IpBlock
from apps.admin.domain.services.auto_block_rules import auto_block_exempt, triggers_auto_block
from apps.admin.domain.entities.access_event_entity import AccessEventKind
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

PASSWORD = "correct-horse-battery"
OPERATOR_IP = ("198.51.100.20", 50000)
ATTACKER_IP = "203.0.113.50"
SETTING_PATH = "/admin/security/settings/auto-defense"


@pytest.fixture(autouse=True)
def clean_admin_tables():
    with session_scope() as session:
        session.execute(
            text(
                "truncate access_event, ip_block, admin_session, admin_audit, security_setting, admin_user"
                " restart identity cascade"
            )
        )
    use_case = get_admin_user_use_case()
    use_case.upsert("ops", PASSWORD, "operator")
    use_case.upsert("viewer", PASSWORD, "viewer")


def _client(username: str, ip=OPERATOR_IP) -> TestClient:
    client = TestClient(app, client=ip)
    assert client.post("/admin/auth/login", json={"username": username, "password": PASSWORD}).status_code == 200
    return client


def _fail_logins(times: int, ip: str = ATTACKER_IP) -> TestClient:
    attacker = TestClient(app, client=(ip, 40000))
    for _ in range(times):
        attacker.post("/admin/auth/login", json={"username": "ops", "password": "wrong-password"})
    return attacker


def _blocks() -> dict[str, dict]:
    return {b["ip"]: b for b in _client("ops").get("/admin/security/ip-blocks").json()}


# ── 규칙 (순수 도메인) ──────────────────────────────


def test_루프백과_알_수_없는_IP는_자동_차단하지_않는다():
    assert auto_block_exempt(None) and auto_block_exempt("127.0.0.1") and auto_block_exempt("::1")
    assert auto_block_exempt("not-an-ip")
    assert not auto_block_exempt(ATTACKER_IP)


def test_관리자_경로의_인증_실패_POST와_스캐너_탐색만_자동_차단을_검사한다():
    assert triggers_auto_block(None, "POST", "/admin/auth/login", 401)
    assert triggers_auto_block(None, "POST", "/admin/auth/login", 429)
    assert triggers_auto_block(AccessEventKind.SCANNER_PROBE, "GET", "/.env", 404)
    assert not triggers_auto_block(None, "GET", "/admin/auth/me", 401)  # 비로그인 방문자의 세션 확인
    assert not triggers_auto_block(None, "POST", "/admin/auth/login", 200)


# ── 설정 API ──────────────────────────────


def test_배선_검증_myself는_로그인_없이_200():
    assert TestClient(app).get("/admin/security/settings/myself").status_code == 200


def test_자동_방어는_기본으로_켜져_있고_일반_회원도_규칙을_볼_수_있다():
    body = _client("viewer", ip=("198.51.100.21", 50000)).get(SETTING_PATH).json()
    assert body["enabled"] is True
    assert body["updated_by"] is None
    rules = {r["rule"]: r for r in body["rules"]}
    assert rules["brute_force_login"] == {
        "rule": "brute_force_login", "title": "로그인 실패", "threshold": 10, "window_minutes": 15,
        "block_minutes": 60, "repeat_block_minutes": 1440,
    }
    assert rules["scanner_probe"]["threshold"] == 5


def test_자동_방어_설정은_로그인이_필요하다():
    assert TestClient(app).get(SETTING_PATH).status_code == 401


def test_자동_방어를_끄고_켜는_것은_관리자만_하고_감사에_남는다():
    viewer = _client("viewer", ip=("198.51.100.21", 50000))
    assert viewer.put(SETTING_PATH, json={"enabled": False}).json()["error"]["code"] == "FORBIDDEN_ROLE"

    ops = _client("ops")
    off = ops.put(SETTING_PATH, json={"enabled": False}).json()
    assert (off["enabled"], off["updated_by"]) == (False, "ops")
    assert ops.get(SETTING_PATH).json()["enabled"] is False
    ops.put(SETTING_PATH, json={"enabled": True})
    audit = [(a["action"], a["detail"]) for a in ops.get("/admin/security/audit").json()["items"]]
    assert audit[:2] == [("auto_defense.toggle", "켬"), ("auto_defense.toggle", "끔")]


# ── 자동 차단 ──────────────────────────────


def test_같은_IP에서_로그인이_10번_틀리면_1시간_자동_차단하고_다음_요청은_403():
    attacker = _fail_logins(10)
    block = _blocks()[ATTACKER_IP]
    assert block["reason"].startswith("자동 차단 · 로그인 실패")
    assert block["created_by"] == "자동 방어"
    expires = datetime.fromisoformat(block["expires_at"]) - datetime.fromisoformat(block["created_at"])
    assert expires == timedelta(hours=1)

    again = attacker.post("/admin/auth/login", json={"username": "ops", "password": PASSWORD})
    assert (again.status_code, again.json()["error"]["code"]) == (403, "IP_BLOCKED")
    audit = _client("ops").get("/admin/security/audit").json()["items"]
    auto = [a for a in audit if a["action"] == "ip_block.auto"]
    assert auto and auto[0]["target"] == ATTACKER_IP and auto[0]["actor"] == "자동 방어"


def test_9번까지는_차단하지_않는다():
    _fail_logins(9)
    assert ATTACKER_IP not in _blocks()


def test_자동_방어를_끄면_실패가_쌓여도_차단하지_않고_로그인_제한만_남는다():
    _client("ops").put(SETTING_PATH, json={"enabled": False})
    attacker = _fail_logins(12)
    assert ATTACKER_IP not in _blocks()
    throttled = attacker.post("/admin/auth/login", json={"username": "ops", "password": PASSWORD})
    assert throttled.status_code == 429


def test_스캐너_경로를_5번_두드리면_24시간_자동_차단한다():
    scanner = TestClient(app, client=("203.0.113.77", 40000))
    for path in ("/.env", "/wp-login.php", "/.git/config", "/phpmyadmin", "/backup.sql"):
        scanner.get(path)
    block = _blocks()["203.0.113.77"]
    assert block["reason"].startswith("자동 차단 · 취약점 스캐너 경로 탐색")
    assert datetime.fromisoformat(block["expires_at"]) - datetime.fromisoformat(block["created_at"]) == timedelta(hours=24)
    assert scanner.get("/admin/auth/providers").status_code == 403


def test_루프백_피어는_로그인이_쌓여도_자동_차단하지_않는다():
    _fail_logins(10, ip="127.0.0.1")
    assert "127.0.0.1" not in _blocks()


def test_이미_수동으로_차단한_IP는_자동_차단으로_덮어쓰지_않는다():
    _client("ops").post("/admin/security/ip-blocks", json={"ip": "203.0.113.77", "reason": "수동", "ttl_minutes": None})
    scanner = TestClient(app, client=("203.0.113.77", 40000))
    for _ in range(6):
        scanner.get("/.env")
    block = _blocks()["203.0.113.77"]
    assert (block["reason"], block["expires_at"], block["created_by"]) == ("수동", None, "ops")


def test_자동_차단이_풀린_뒤_다시_걸리면_더_길게_24시간_차단한다():
    past = datetime.now(UTC) - timedelta(hours=3)
    SqlAlchemyIpBlockRepository().save(
        IpBlock(ip=ATTACKER_IP, reason="자동 차단 · 로그인 실패 10회", created_at=past, expires_at=past + timedelta(hours=1))
    )
    _fail_logins(10)
    block = _blocks()[ATTACKER_IP]
    assert datetime.fromisoformat(block["expires_at"]) - datetime.fromisoformat(block["created_at"]) == timedelta(hours=24)
    assert "재차단" in block["reason"]
