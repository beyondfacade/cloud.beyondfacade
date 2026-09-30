"""관리자 운영 강화 — 계정 규칙·감사 로그·보안 이벤트 검색·보존 정리 (실제 테스트 DB)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.admin.adapter.outbound.repositories.access_event_repository import SqlAlchemyAccessEventRepository
from apps.admin.adapter.outbound.repositories.admin_audit_repository import SqlAlchemyAdminAuditRepository
from apps.admin.adapter.outbound.repositories.admin_session_repository import SqlAlchemyAdminSessionRepository
from apps.admin.adapter.outbound.repositories.ip_block_repository import SqlAlchemyIpBlockRepository
from apps.admin.app.use_cases.housekeeping_interactor import HousekeepingInteractor
from apps.admin.dependencies.admin_dependencies import get_admin_user_use_case
from apps.admin.domain.entities.access_event_entity import AccessEvent, AccessEventKind
from apps.admin.domain.entities.admin_audit_entity import AdminAudit, AuditAction
from apps.admin.domain.entities.admin_user_entity import AdminRole, AdminUser
from apps.admin.domain.entities.ip_block_entity import IpBlock
from apps.admin.domain.services.account_policy import leaves_no_active_operator, password_problem, username_problem
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

OPERATOR_IP = ("198.51.100.20", 50000)
PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def clean_admin_tables():
    with session_scope() as session:
        session.execute(
            text("truncate access_event, ip_block, admin_session, admin_audit, admin_user restart identity cascade")
        )
    use_case = get_admin_user_use_case()
    use_case.upsert("ops", PASSWORD, "operator")
    use_case.upsert("viewer", PASSWORD, "viewer")


def _client(username: str, ip=OPERATOR_IP) -> TestClient:
    client = TestClient(app, client=ip)
    assert client.post("/admin/auth/login", json={"username": username, "password": PASSWORD}).status_code == 200
    return client


def _user(username: str, role: AdminRole, active: bool = True) -> AdminUser:
    return AdminUser(username=username, password_hash="x", role=role, is_active=active)


# ── 계정 규칙 (순수 도메인) ──────────────────────────────


def test_계정명은_소문자_숫자로_시작하는_3에서_32자만_허용한다():
    assert username_problem("ops.kim-2") is None
    assert username_problem("ab") is not None
    assert username_problem("Admin") is not None
    assert username_problem("-ops") is not None
    assert username_problem("a" * 33) is not None


def test_비밀번호는_12자_미만이면_문제를_돌려준다():
    assert password_problem("short-pass") is not None
    assert password_problem("long-enough-pass") is None


def test_마지막_활성_운영자를_강등하거나_정지하면_운영자가_0명이_된다():
    users = [_user("ops", AdminRole.OPERATOR), _user("viewer", AdminRole.VIEWER)]
    assert leaves_no_active_operator(users, "ops", AdminRole.VIEWER, True)
    assert leaves_no_active_operator(users, "ops", AdminRole.OPERATOR, False)
    assert not leaves_no_active_operator(users, "viewer", AdminRole.OPERATOR, False)


def test_정지된_운영자는_남은_운영자로_세지_않는다():
    users = [_user("ops", AdminRole.OPERATOR), _user("old", AdminRole.OPERATOR, active=False)]
    assert leaves_no_active_operator(users, "ops", AdminRole.VIEWER, True)
    users.append(_user("ops2", AdminRole.OPERATOR))
    assert not leaves_no_active_operator(users, "ops", AdminRole.VIEWER, True)


# ── 감사 로그 ─────────────────────────────────────────


def test_IP_차단과_해제는_감사_로그에_남는다():
    client = _client("ops")
    client.post("/admin/security/ip-blocks", json={"ip": "203.0.113.99", "reason": "스캐너", "ttl_minutes": 60})
    client.delete("/admin/security/ip-blocks/203.0.113.99")
    items = client.get("/admin/security/audit").json()["items"]
    assert [item["action"] for item in items] == ["ip_block.delete", "ip_block.create"]
    assert items[1]["actor"] == "ops"
    assert items[1]["target"] == "203.0.113.99"
    assert items[1]["ip"] == "198.51.100.20"
    assert "스캐너" in items[1]["detail"]


def test_감사_로그는_조회_관리자도_볼_수_있고_조치별로_거른다():
    ops = _client("ops")
    ops.post("/admin/security/ip-blocks", json={"ip": "203.0.113.1", "reason": "", "ttl_minutes": None})
    ops.post("/admin/security/ip-blocks", json={"ip": "203.0.113.2", "reason": "", "ttl_minutes": None})
    ops.delete("/admin/security/ip-blocks/203.0.113.1")
    viewer = _client("viewer", ip=("198.51.100.21", 50000))
    response = viewer.get("/admin/security/audit", params={"action": "ip_block.create"})
    assert response.status_code == 200
    assert [item["target"] for item in response.json()["items"]] == ["203.0.113.2", "203.0.113.1"]


def test_감사_로그는_before_id로_다음_쪽을_이어_받는다():
    ops = _client("ops")
    for n in range(3):
        ops.post("/admin/security/ip-blocks", json={"ip": f"203.0.113.{n + 10}", "reason": "", "ttl_minutes": None})
    first = ops.get("/admin/security/audit", params={"limit": 2}).json()
    assert len(first["items"]) == 2
    assert first["next_before_id"] == first["items"][-1]["id"]
    second = ops.get("/admin/security/audit", params={"limit": 2, "before_id": first["next_before_id"]}).json()
    assert [item["target"] for item in second["items"]] == ["203.0.113.10"]
    assert second["next_before_id"] is None


def test_감사_로그는_로그인이_필요하다():
    assert TestClient(app).get("/admin/security/audit").status_code == 401
    assert TestClient(app).get("/admin/security/audit/myself").status_code == 200


# ── 보안 이벤트 검색 ─────────────────────────────────────


def _seed_events(now: datetime) -> None:
    repository = SqlAlchemyAccessEventRepository()
    rows = [  # 실제처럼 오래된 것부터 쌓는다 — 쪽 나눔은 id 역순
        (AccessEventKind.SERVER_ERROR, "10.0.0.1", "/stores", 500, 30),  # 24시간 창 밖
        (AccessEventKind.LOGIN_FAILED, "203.0.113.5", "/admin/auth/login", 401, 3),
        (AccessEventKind.SCANNER_PROBE, "203.0.113.6", "/wp-login.php", 404, 2),
        (AccessEventKind.SCANNER_PROBE, "203.0.113.5", "/.env", 404, 1),
    ]
    for kind, ip, path, status, hours_ago in rows:
        repository.add(
            AccessEvent(
                occurred_at=now - timedelta(hours=hours_ago), kind=kind, ip=ip, method="GET", path=path,
                status_code=status,
            )
        )


def test_보안_이벤트는_종류와_IP와_기간으로_거른다():
    _seed_events(datetime.now(UTC))
    viewer = _client("viewer")
    by_kind = viewer.get("/admin/security/events", params={"kind": "scanner_probe"}).json()["items"]
    assert {item["path"] for item in by_kind} == {"/.env", "/wp-login.php"}
    by_ip = viewer.get("/admin/security/events", params={"ip": "203.0.113.5"}).json()["items"]
    assert [item["kind"] for item in by_ip] == ["scanner_probe", "login_failed"]
    week = viewer.get("/admin/security/events", params={"hours": 168, "kind": "server_error"}).json()["items"]
    assert [item["path"] for item in week] == ["/stores"]


def test_보안_이벤트는_최신순으로_쪽을_나눈다():
    _seed_events(datetime.now(UTC))
    viewer = _client("viewer")
    first = viewer.get("/admin/security/events", params={"limit": 2, "kind": "scanner_probe"}).json()
    assert len(first["items"]) == 2
    assert first["next_before_id"] is None  # 딱 떨어지면 다음 쪽이 없다
    page = viewer.get("/admin/security/events", params={"limit": 1, "kind": "scanner_probe"}).json()
    rest = viewer.get(
        "/admin/security/events", params={"limit": 1, "kind": "scanner_probe", "before_id": page["next_before_id"]}
    ).json()
    assert page["items"][0]["path"] == "/.env"
    assert rest["items"][0]["path"] == "/wp-login.php"


def test_보안_이벤트_검색은_모르는_종류를_422로_거절한다():
    response = _client("viewer").get("/admin/security/events", params={"kind": "nope"})
    assert response.status_code == 422


# ── 보존 정리 ─────────────────────────────────────────


def test_보존_정리는_오래된_이벤트_감사_만료_세션_만료_차단만_지운다():
    now = datetime(2026, 9, 30, 3, 30, tzinfo=UTC)
    events = SqlAlchemyAccessEventRepository()
    for days in (1, 120):
        events.add(
            AccessEvent(
                occurred_at=now - timedelta(days=days), kind=AccessEventKind.SCANNER_PROBE, ip="203.0.113.5",
                method="GET", path="/.env", status_code=404,
            )
        )
    audit = SqlAlchemyAdminAuditRepository()
    for days in (10, 400):
        audit.add(
            AdminAudit(occurred_at=now - timedelta(days=days), action=AuditAction.PROBE_RUN, actor_username="ops",
                       target="all")
        )
    ip_blocks = SqlAlchemyIpBlockRepository()
    ip_blocks.save(IpBlock(ip="203.0.113.7", reason="", created_at=now, expires_at=now - timedelta(minutes=1)))
    ip_blocks.save(IpBlock(ip="203.0.113.8", reason="", created_at=now, expires_at=None))
    sessions = SqlAlchemyAdminSessionRepository()
    _client("ops")  # 방금 만든 유효 세션 1개

    result = HousekeepingInteractor(
        events=events, audit=audit, sessions=sessions, ip_blocks=ip_blocks, clock=lambda: now
    ).run()

    assert (result.access_events, result.audit_entries, result.ip_blocks) == (1, 1, 1)
    with session_scope() as session:
        assert session.execute(text("select count(*) from access_event where kind='scanner_probe'")).scalar_one() == 1
        assert session.execute(text("select count(*) from admin_audit")).scalar_one() == 1
        assert session.execute(text("select ip from ip_block")).scalars().all() == ["203.0.113.8"]


def test_보존_정리는_만료된_세션을_지운다():
    _client("ops")
    later = datetime.now(UTC) + timedelta(days=30)
    result = HousekeepingInteractor(
        events=SqlAlchemyAccessEventRepository(), audit=SqlAlchemyAdminAuditRepository(),
        sessions=SqlAlchemyAdminSessionRepository(), ip_blocks=SqlAlchemyIpBlockRepository(), clock=lambda: later,
    ).run()
    assert result.sessions == 1
