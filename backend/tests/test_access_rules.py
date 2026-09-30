"""디바이스·IP 화이트리스트/블랙리스트 — 디바이스 쿠키 발급, 목록 관리, 차단·예외 적용 (실제 테스트 DB)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.admin.adapter.outbound.repositories.access_rule_repository import SqlAlchemyAccessRuleRepository
from apps.admin.adapter.outbound.repositories.ip_block_repository import SqlAlchemyIpBlockRepository
from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from apps.admin.domain.entities.access_rule_entity import AccessRule, RulePolicy, RuleTarget
from apps.admin.domain.entities.client_entity import Client
from apps.admin.domain.entities.ip_block_entity import IpBlock
from apps.admin.domain.services.access_rule_targets import TARGETS
from apps.admin.domain.services.device_id import is_device_id, new_device_id
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

PASSWORD = "correct-horse-battery"
OPERATOR_IP = ("198.51.100.20", 50000)
ATTACKER_IP = "203.0.113.50"
RULES = "/admin/security/access-rules"
DEVICE_COOKIE = "metabole_device"
MY_DEVICE = "Mm" * 11
ATTACKER_DEVICE = "Xx" * 11
TRUSTED_DEVICE = "Tt" * 11


@pytest.fixture(autouse=True)
def clean_admin_tables():
    with session_scope() as session:
        session.execute(
            text(
                "truncate access_event, ip_block, access_rule, admin_session, admin_audit, security_setting, admin_user"
                " restart identity cascade"
            )
        )
    use_case = get_admin_user_use_case()
    use_case.upsert("ops", PASSWORD, "operator")
    use_case.upsert("viewer", PASSWORD, "viewer")


def _device_client(ip: str, device: str | None = None) -> TestClient:
    client = TestClient(app, client=(ip, 40000))
    if device:
        client.cookies.set(DEVICE_COOKIE, device)
    return client


def _client(username: str, ip=OPERATOR_IP, device: str = MY_DEVICE) -> TestClient:
    client = _device_client(ip[0], device)
    assert client.post("/admin/auth/login", json={"username": username, "password": PASSWORD}).status_code == 200
    return client


def _fail_logins(client: TestClient, times: int) -> None:
    for _ in range(times):
        client.post("/admin/auth/login", json={"username": "ops", "password": "wrong-password"})


def _add(client: TestClient, policy: str, target: str, value: str, **extra):
    return client.post(RULES, json={"policy": policy, "target": target, "value": value, **extra})


def _audit_actions() -> list[tuple[str, str]]:
    items = _client("ops").get("/admin/security/audit").json()["items"]
    return [(e["action"], e["target"]) for e in items if e["action"].startswith("access_rule")]


# ── 규칙 대상 (순수 도메인) ──────────────────────────────


def test_IP_대상은_단일_주소와_대역을_받아_정규화한다():
    ip = TARGETS[RuleTarget.IP]
    assert ip.normalize(" 203.0.113.7 ") == "203.0.113.7"
    assert ip.normalize("10.1.2.3/8") == "10.0.0.0/8"
    assert ip.normalize("2001:db8::/48") == "2001:db8::/48"
    for bad in ("abc", "0.0.0.0/0", "10.0.0.0/7", "2001:db8::/16", ""):
        with pytest.raises(ValueError):
            ip.normalize(bad)


def test_IP_대상은_대역_안의_주소에만_맞는다():
    ip = TARGETS[RuleTarget.IP]
    assert ip.matches("10.0.0.0/8", Client(ip="10.200.3.4"))
    assert not ip.matches("10.0.0.0/8", Client(ip="11.0.0.1"))
    assert not ip.matches("10.0.0.0/8", Client(ip="::1"))
    assert not ip.matches("10.0.0.0/8", Client(ip=None))


def test_디바이스_대상은_발급한_ID_형식만_받고_정확히_같을_때만_맞는다():
    device = TARGETS[RuleTarget.DEVICE]
    assert device.normalize(f" {MY_DEVICE} ") == MY_DEVICE
    for bad in ("short", "x" * 23, "!" * 22):
        with pytest.raises(ValueError):
            device.normalize(bad)
    assert device.matches(MY_DEVICE, Client(ip=None, device_id=MY_DEVICE))
    assert not device.matches(MY_DEVICE, Client(ip=None, device_id=ATTACKER_DEVICE))


def test_새_디바이스_ID는_22자_URL_안전_문자열이고_매번_다르다():
    first, second = new_device_id(), new_device_id()
    assert is_device_id(first) and is_device_id(second) and first != second


# ── 디바이스 쿠키와 기록 ──────────────────────────────


def test_배선_검증_myself는_로그인_없이_200():
    assert TestClient(app).get(f"{RULES}/myself").status_code == 200


def test_관리자_경로_첫_요청에_디바이스_쿠키를_발급하고_있으면_다시_발급하지_않는다():
    client = TestClient(app, client=(ATTACKER_IP, 40000))
    first = client.get("/admin/auth/providers")
    cookie = first.headers["set-cookie"]
    assert cookie.startswith(f"{DEVICE_COOKIE}=") and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert is_device_id(client.cookies[DEVICE_COOKIE])
    assert "set-cookie" not in client.get("/admin/auth/providers").headers
    assert "set-cookie" not in TestClient(app).get("/health").headers


def test_보안_이벤트에_디바이스_ID와_브라우저_정보가_남는다():
    attacker = _device_client(ATTACKER_IP, ATTACKER_DEVICE)
    attacker.headers["User-Agent"] = "Mozilla/5.0 (Macintosh) Safari/605.1.15"
    _fail_logins(attacker, 1)
    events = _client("ops").get("/admin/security/events", params={"ip": ATTACKER_IP}).json()["items"]
    assert events[0]["device_id"] == ATTACKER_DEVICE
    assert events[0]["user_agent"] == "Mozilla/5.0 (Macintosh) Safari/605.1.15"


def test_지금_디바이스를_조회하면_ID와_목록_상태를_돌려준다():
    ops = _client("ops")
    assert ops.get(f"{RULES}/current-device").json() == {
        "device_id": MY_DEVICE, "user_agent": "testclient", "allowed": False, "denied": False,
    }
    _add(ops, "allow", "device", MY_DEVICE)
    assert ops.get(f"{RULES}/current-device").json()["allowed"] is True


# ── 목록 관리 API ──────────────────────────────


def test_목록_조회는_로그인이_필요하다():
    assert TestClient(app).get(RULES).status_code == 401


def test_일반_회원은_목록을_볼_수만_있고_추가하면_403():
    viewer = _client("viewer", ip=("198.51.100.21", 50000))
    assert viewer.get(RULES).json() == []
    response = _add(viewer, "allow", "ip", "10.0.0.0/8")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_관리자가_IP_대역을_화이트리스트에_넣으면_정규화되어_목록과_감사_로그에_남는다():
    ops = _client("ops")
    response = _add(ops, "allow", "ip", "10.1.2.3/8", note="사무실")
    assert response.status_code == 201
    rule = response.json()
    assert rule | {"id": 0, "created_at": ""} == {
        "id": 0, "policy": "allow", "target": "ip", "value": "10.0.0.0/8", "note": "사무실",
        "created_at": "", "expires_at": None, "created_by": "ops",
    }
    assert [r["value"] for r in ops.get(RULES).json()] == ["10.0.0.0/8"]
    assert _audit_actions() == [("access_rule.create", "10.0.0.0/8")]


def test_기간을_주면_만료_시각이_생긴다():
    rule = _add(_client("ops"), "deny", "device", ATTACKER_DEVICE, ttl_minutes=60).json()
    assert rule["expires_at"] is not None


def test_형식이_틀리거나_너무_넓은_대역은_400_INVALID_ACCESS_RULE():
    ops = _client("ops")
    for target, value in (("ip", "not-an-ip"), ("ip", "0.0.0.0/0"), ("device", "short")):
        response = _add(ops, "allow", target, value)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_ACCESS_RULE"


def test_IP_블랙리스트는_IP_차단_목록에서만_받는다():
    response = _add(_client("ops"), "deny", "ip", ATTACKER_IP)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ACCESS_RULE"


def test_같은_목록에_같은_값은_409_ACCESS_RULE_EXISTS():
    ops = _client("ops")
    assert _add(ops, "allow", "ip", "10.0.0.0/8").status_code == 201
    response = _add(ops, "allow", "ip", "10.9.9.9/8")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACCESS_RULE_EXISTS"


def test_만료된_항목은_같은_값으로_다시_넣을_수_있다():
    past = datetime.now(UTC) - timedelta(days=2)
    SqlAlchemyAccessRuleRepository().save(
        AccessRule(policy=RulePolicy.DENY, target=RuleTarget.DEVICE, value=ATTACKER_DEVICE, note="",
                   created_at=past, expires_at=past + timedelta(hours=1))
    )
    assert _add(_client("ops"), "deny", "device", ATTACKER_DEVICE).status_code == 201


def test_지금_쓰는_내_디바이스는_블랙리스트에_넣을_수_없다():
    response = _add(_client("ops"), "deny", "device", MY_DEVICE)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SELF_BLOCK"


def test_삭제하면_204와_감사_로그_없는_항목은_404():
    ops = _client("ops")
    rule_id = _add(ops, "allow", "ip", "192.0.2.0/24").json()["id"]
    assert ops.delete(f"{RULES}/{rule_id}").status_code == 204
    assert ops.get(RULES).json() == []
    assert ("access_rule.delete", "192.0.2.0/24") in _audit_actions()
    missing = ops.delete(f"{RULES}/{rule_id}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "ACCESS_RULE_NOT_FOUND"


# ── 적용 ──────────────────────────────


def test_블랙리스트_디바이스는_관리자_경로에서_403_DEVICE_BLOCKED_같은_IP의_다른_디바이스는_통과():
    _add(_client("ops"), "deny", "device", ATTACKER_DEVICE)
    blocked = _device_client(ATTACKER_IP, ATTACKER_DEVICE).get("/admin/auth/providers")
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "DEVICE_BLOCKED"
    assert _device_client(ATTACKER_IP, "Oo" * 11).get("/admin/auth/providers").status_code == 200


def test_화이트리스트_IP는_실패가_쌓여도_자동_차단과_로그인_제한에_걸리지_않는다():
    _add(_client("ops"), "allow", "ip", "203.0.113.0/24")
    office = _device_client(ATTACKER_IP)
    _fail_logins(office, 12)
    assert SqlAlchemyIpBlockRepository().get(ATTACKER_IP) is None
    assert office.post("/admin/auth/login", json={"username": "ops", "password": PASSWORD}).status_code == 200


def test_화이트리스트_디바이스는_같은_IP가_자동_차단돼도_들어온다():
    _add(_client("ops"), "allow", "device", TRUSTED_DEVICE)
    _fail_logins(_device_client(ATTACKER_IP, ATTACKER_DEVICE), 10)
    assert _device_client(ATTACKER_IP, ATTACKER_DEVICE).get("/admin/auth/providers").status_code == 403

    trusted = _device_client(ATTACKER_IP, TRUSTED_DEVICE)
    assert trusted.post("/admin/auth/login", json={"username": "ops", "password": PASSWORD}).status_code == 200


def test_수동_IP_차단은_화이트리스트_디바이스도_막는다():
    _add(_client("ops"), "allow", "device", TRUSTED_DEVICE)
    SqlAlchemyIpBlockRepository().save(IpBlock(ip=ATTACKER_IP, reason="수동 차단", created_at=datetime.now(UTC)))
    response = _device_client(ATTACKER_IP, TRUSTED_DEVICE).get("/admin/auth/providers")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "IP_BLOCKED"
