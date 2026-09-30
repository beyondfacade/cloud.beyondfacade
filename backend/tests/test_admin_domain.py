"""admin BC 도메인 — 비밀번호·세션 토큰·스캐너 경로·알림 규칙·차단 만료."""

from datetime import UTC, datetime, timedelta

from apps.admin.domain.entities.access_event_entity import AccessEvent, AccessEventKind
from apps.admin.domain.entities.admin_session_entity import AdminSession
from apps.admin.domain.entities.admin_user_entity import AdminRole
from apps.admin.domain.entities.ip_block_entity import IpBlock
from apps.admin.domain.services.alert_rules import evaluate_alerts
from apps.admin.domain.services.password_hasher import hash_password, verify_password
from apps.admin.domain.services.scanner_paths import is_scanner_probe
from apps.admin.domain.services.session_token import hash_token, new_session_token

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def _event(kind: AccessEventKind, ip: str | None = "203.0.113.10", minutes_ago: int = 1) -> AccessEvent:
    return AccessEvent(
        occurred_at=NOW - timedelta(minutes=minutes_ago),
        kind=kind,
        ip=ip,
        method="POST",
        path="/admin/auth/login",
        status_code=401,
    )


def test_비밀번호는_해시로만_저장되고_원문으로_검증된다():
    encoded = hash_password("correct horse")
    assert "correct horse" not in encoded
    assert verify_password("correct horse", encoded)
    assert not verify_password("wrong", encoded)


def test_같은_비밀번호도_솔트가_달라_해시가_다르다():
    assert hash_password("same") != hash_password("same")


def test_형식이_깨진_해시는_검증에_실패한다():
    assert not verify_password("x", "not-a-hash")


def test_세션_토큰은_원문과_해시가_다르고_해시는_결정적이다():
    raw, token_hash = new_session_token()
    assert raw != token_hash
    assert hash_token(raw) == token_hash


def test_세션은_만료_시각이_지나면_만료다():
    session = AdminSession(token_hash="h", admin_user_id=1, created_at=NOW, expires_at=NOW + timedelta(hours=1))
    assert not session.is_expired(NOW)
    assert session.is_expired(NOW + timedelta(hours=1))


def test_운영_관리자만_변경_권한이_있다():
    assert AdminRole.OPERATOR.can_operate
    assert not AdminRole.VIEWER.can_operate


def test_IP_차단은_만료_전까지만_유효하고_무기한도_있다():
    timed = IpBlock(ip="1.2.3.4", reason="r", created_at=NOW, expires_at=NOW + timedelta(minutes=10))
    forever = IpBlock(ip="1.2.3.5", reason="r", created_at=NOW, expires_at=None)
    assert timed.is_active(NOW)
    assert not timed.is_active(NOW + timedelta(minutes=10))
    assert forever.is_active(NOW + timedelta(days=365))


def test_스캐너_경로를_알아본다():
    for path in ("/.env", "/wp-login.php", "/.git/config", "/phpmyadmin/index.php", "/admin/config.php"):
        assert is_scanner_probe(path), path
    for path in ("/regions/geojson", "/admin/security/overview", "/stores"):
        assert not is_scanner_probe(path), path


def test_같은_IP_로그인_실패가_5회를_넘으면_high_알림():
    events = [_event(AccessEventKind.LOGIN_FAILED) for _ in range(5)]
    alerts = evaluate_alerts(events, blocked_ips=set(), now=NOW)
    assert len(alerts) == 1
    alert = alerts[0]
    assert (alert.rule, alert.severity, alert.ip, alert.count) == ("brute_force_login", "high", "203.0.113.10", 5)
    assert not alert.blocked


def test_로그인_실패_10회면_critical이고_차단_여부가_표시된다():
    events = [_event(AccessEventKind.LOGIN_FAILED) for _ in range(10)]
    alert = evaluate_alerts(events, blocked_ips={"203.0.113.10"}, now=NOW)[0]
    assert alert.severity == "critical"
    assert alert.blocked


def test_창_밖의_실패는_세지_않는다():
    events = [_event(AccessEventKind.LOGIN_FAILED, minutes_ago=30) for _ in range(9)]
    assert evaluate_alerts(events, blocked_ips=set(), now=NOW) == []


def test_스캐너_탐색_3회면_medium_알림():
    events = [_event(AccessEventKind.SCANNER_PROBE, ip="198.51.100.7") for _ in range(3)]
    alert = evaluate_alerts(events, blocked_ips=set(), now=NOW)[0]
    assert (alert.rule, alert.severity, alert.ip) == ("scanner_probe", "medium", "198.51.100.7")


def test_서버_오류_급증은_IP와_무관하게_합산한다():
    events = [_event(AccessEventKind.SERVER_ERROR, ip=f"10.0.0.{i}") for i in range(5)]
    alert = evaluate_alerts(events, blocked_ips=set(), now=NOW)[0]
    assert (alert.rule, alert.severity, alert.ip, alert.count) == ("server_error_burst", "high", None, 5)


def test_알림은_심각도_순으로_정렬된다():
    events = [_event(AccessEventKind.SCANNER_PROBE, ip="198.51.100.7") for _ in range(3)]
    events += [_event(AccessEventKind.LOGIN_FAILED) for _ in range(10)]
    assert [a.severity for a in evaluate_alerts(events, blocked_ips=set(), now=NOW)] == ["critical", "medium"]
