"""공개 회원가입·이메일 로그인·구글 로그인·등급(일반=viewer 읽기, 관리자=operator 쓰기) — 실제 테스트 DB."""

import base64
import hashlib
import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.admin.adapter.outbound.google.google_identity_adapter import GoogleIdentityAdapter
from apps.admin.adapter.outbound.repositories.access_event_repository import SqlAlchemyAccessEventRepository
from apps.admin.adapter.outbound.repositories.admin_audit_repository import SqlAlchemyAdminAuditRepository
from apps.admin.adapter.outbound.repositories.admin_session_repository import SqlAlchemyAdminSessionRepository
from apps.admin.adapter.outbound.repositories.admin_user_repository import SqlAlchemyAdminUserRepository
from apps.admin.app.dtos.google_identity_dto import GoogleIdentityDto
from apps.admin.app.ports.output.google_identity_port import GoogleIdentityPort
from apps.admin.app.use_cases.admin_session_interactor import AdminSessionInteractor
from apps.admin.dependencies.admin_dependencies import get_admin_session_use_case, get_admin_user_use_case
from apps.admin.domain.services.account_policy import email_problem, normalize_email, username_candidates
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

IP = ("198.51.100.40", 50000)
PASSWORD = "correct-horse-battery"
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"


class FakeGoogle(GoogleIdentityPort):
    """code → 구글 신원. exchange에 넘어온 verifier를 남겨 PKCE 배선을 검증한다."""

    def __init__(self, configured: bool = True) -> None:
        self.configured = configured
        self.identities: dict[str, GoogleIdentityDto] = {}
        self.verifiers: list[str] = []

    def is_configured(self) -> bool:
        return self.configured

    def authorization_url(self, state: str, code_challenge: str) -> str:
        return f"{GOOGLE_AUTH}?state={state}&code_challenge={code_challenge}&code_challenge_method=S256"

    def exchange(self, code: str, code_verifier: str) -> GoogleIdentityDto | None:
        self.verifiers.append(code_verifier)
        return self.identities.get(code)


@pytest.fixture
def google():
    fake = FakeGoogle()
    app.dependency_overrides[get_admin_session_use_case] = lambda: AdminSessionInteractor(
        users=SqlAlchemyAdminUserRepository(),
        sessions=SqlAlchemyAdminSessionRepository(),
        events=SqlAlchemyAccessEventRepository(),
        audit=SqlAlchemyAdminAuditRepository(),
        google=fake,
    )
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clean_admin_tables():
    with session_scope() as session:
        session.execute(
            text("truncate access_event, ip_block, admin_session, admin_audit, admin_user restart identity cascade")
        )
    get_admin_user_use_case().upsert("ops", PASSWORD, "operator")


def _signup(client: TestClient, username: str = "kim", email: str = "kim@example.com", password: str = PASSWORD):
    return client.post("/admin/auth/signup", json={"username": username, "email": email, "password": password})


def _google_login(client: TestClient, google: FakeGoogle, identity: GoogleIdentityDto, next_path: str = "/admin"):
    start = client.get("/admin/auth/google/start", params={"next": next_path}, follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    google.identities["code-1"] = identity
    return client.get(
        "/admin/auth/google/callback", params={"code": "code-1", "state": state}, follow_redirects=False
    )


def _identity(sub: str = "g-1", email: str = "Lee.Young+news@gmail.com", verified: bool = True) -> GoogleIdentityDto:
    return GoogleIdentityDto(sub=sub, email=email, email_verified=verified)


def _count(sql: str) -> int:
    with session_scope() as session:
        return session.execute(text(sql)).scalar_one()


# ── 도메인 규칙 ─────────────────────────────────────────


def test_이메일은_앞뒤_공백을_빼고_소문자로_맞춘다():
    assert normalize_email("  Kim@Example.COM ") == "kim@example.com"


def test_이메일_형식이_아니면_문제를_알려준다():
    assert email_problem("kim@example.com") is None
    assert email_problem("kim") is not None
    assert email_problem("kim@") is not None
    assert email_problem("a b@example.com") is not None


def test_구글_계정명은_이메일_앞부분을_규칙에_맞게_다듬고_겹치면_번호를_붙인다():
    candidates = username_candidates("Lee.Young+news@gmail.com")
    assert [next(candidates) for _ in range(3)] == ["lee.young.news", "lee.young.news2", "lee.young.news3"]


def test_이메일_앞부분이_너무_짧으면_user를_붙인다():
    assert next(username_candidates("ab@example.com")) == "ab.user"
    assert next(username_candidates("+@example.com")) == "user"


# ── 회원가입·로그인 ──────────────────────────────────────


def test_가입하면_일반_등급으로_바로_로그인된다():
    client = TestClient(app, client=IP)
    response = _signup(client)
    assert response.status_code == 201
    assert response.json() == {"username": "kim", "role": "viewer", "can_operate": False}
    assert "metabole_admin" in response.cookies
    assert client.get("/admin/auth/me").json()["username"] == "kim"


def test_일반_회원은_관리자_페이지를_읽지만_쓰기는_403():
    client = TestClient(app, client=IP)
    _signup(client)
    assert client.get("/admin/security/overview").status_code == 200
    assert client.get("/admin/users").status_code == 200
    blocked = client.post("/admin/security/ip-blocks", json={"ip": "203.0.113.9", "reason": "x"})
    assert blocked.status_code == 403
    assert blocked.json()["error"]["message"] == "관리자 권한이 필요합니다."


def test_이메일로도_로그인하고_대소문자를_가리지_않는다():
    _signup(TestClient(app, client=IP))
    client = TestClient(app, client=IP)
    response = client.post("/admin/auth/login", json={"username": "KIM@example.com", "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["username"] == "kim"


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"username": "ops", "email": "new@example.com"}, 409, "USERNAME_TAKEN"),
        ({"username": "Bad Name", "email": "new@example.com"}, 400, "INVALID_USERNAME"),
        ({"username": "new.one", "email": "not-an-email"}, 400, "INVALID_EMAIL"),
        ({"username": "new.one", "email": "new@example.com", "password": "short"}, 400, "WEAK_PASSWORD"),
    ],
)
def test_가입_입력이_틀리면_이유를_코드로_알려준다(body, status, code):
    response = TestClient(app, client=IP).post("/admin/auth/signup", json={"password": PASSWORD, **body})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_이미_쓰는_이메일로는_가입할_수_없다():
    _signup(TestClient(app, client=IP))
    response = _signup(TestClient(app, client=IP), username="kim2", email="KIM@example.com")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"


def test_같은_IP에서_한_시간에_5번을_넘게_가입하면_429():
    for n in range(5):
        assert _signup(TestClient(app, client=IP), f"user{n}", f"user{n}@example.com").status_code == 201
    response = _signup(TestClient(app, client=IP), "user9", "user9@example.com")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
    assert _count("select count(*) from access_event where kind = 'signup'") == 5


def test_일반_회원을_CLI로_관리자로_올리면_쓰기가_열린다():
    client = TestClient(app, client=IP)
    _signup(client)
    get_admin_user_use_case().set_role("kim", "operator")
    assert client.get("/admin/auth/me").json() == {"username": "kim", "role": "operator", "can_operate": True}


def test_인사팀_목록은_이메일과_가입_방식을_담고_이메일로도_찾는다(google):
    _signup(TestClient(app, client=IP))
    _google_login(TestClient(app, client=IP), google, _identity())
    ops = TestClient(app, client=IP)
    ops.post("/admin/auth/login", json={"username": "ops", "password": PASSWORD})
    items = {item["username"]: item for item in ops.get("/admin/users").json()["items"]}
    assert items["kim"]["email"] == "kim@example.com"
    assert (items["kim"]["has_password"], items["kim"]["has_google"]) == (True, False)
    assert (items["lee.young.news"]["has_password"], items["lee.young.news"]["has_google"]) == (False, True)
    assert items["ops"]["email"] is None
    found = ops.get("/admin/users", params={"q": "gmail"}).json()["items"]
    assert [item["username"] for item in found] == ["lee.young.news"]


# ── 구글 로그인 ─────────────────────────────────────────


def test_구글이_설정되지_않으면_providers가_false이고_시작은_로그인_화면으로_돌려보낸다(google):
    google.configured = False
    client = TestClient(app, client=IP)
    assert client.get("/admin/auth/providers").json() == {"google": False}
    start = client.get("/admin/auth/google/start", follow_redirects=False)
    assert start.status_code == 302
    assert start.headers["location"] == "/login?error=GOOGLE_NOT_CONFIGURED"


def test_구글_시작은_state와_PKCE_S256을_실어_구글로_보낸다(google):
    client = TestClient(app, client=IP)
    assert client.get("/admin/auth/providers").json() == {"google": True}
    start = client.get("/admin/auth/google/start", follow_redirects=False)
    assert start.status_code == 302
    query = parse_qs(urlparse(start.headers["location"]).query)
    assert start.headers["location"].startswith(GOOGLE_AUTH)
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["state"][0]) >= 32
    assert "metabole_oauth" in start.cookies


def test_처음_보는_구글_계정은_일반_회원으로_가입되고_next로_돌아간다(google):
    client = TestClient(app, client=IP)
    callback = _google_login(client, google, _identity(), next_path="/admin/security")
    assert callback.status_code == 302
    assert callback.headers["location"] == "/admin/security"
    assert client.get("/admin/auth/me").json() == {"username": "lee.young.news", "role": "viewer", "can_operate": False}
    assert _count("select count(*) from access_event where kind = 'signup'") == 1


def test_구글_토큰_교환에는_시작할_때_만든_PKCE_verifier가_쓰인다(google):
    client = TestClient(app, client=IP)
    start = client.get("/admin/auth/google/start", follow_redirects=False)
    query = parse_qs(urlparse(start.headers["location"]).query)
    google.identities["code-1"] = _identity()
    client.get("/admin/auth/google/callback", params={"code": "code-1", "state": query["state"][0]}, follow_redirects=False)
    digest = hashlib.sha256(google.verifiers[0].encode()).digest()
    assert base64.urlsafe_b64encode(digest).rstrip(b"=").decode() == query["code_challenge"][0]


def test_같은_구글_계정은_두_번째에도_같은_계정으로_들어온다(google):
    _google_login(TestClient(app, client=IP), google, _identity())
    client = TestClient(app, client=IP)
    _google_login(client, google, _identity(email="changed@gmail.com"))
    assert client.get("/admin/auth/me").json()["username"] == "lee.young.news"
    assert _count("select count(*) from admin_user where google_sub is not null") == 1


def test_state가_다르면_세션_없이_로그인_화면으로_돌려보낸다(google):
    client = TestClient(app, client=IP)
    client.get("/admin/auth/google/start", follow_redirects=False)
    google.identities["code-1"] = _identity()
    callback = client.get(
        "/admin/auth/google/callback", params={"code": "code-1", "state": "forged"}, follow_redirects=False
    )
    assert callback.headers["location"] == "/login?error=OAUTH_STATE_MISMATCH"
    assert client.get("/admin/auth/me").status_code == 401
    assert google.verifiers == []


def test_구글에서_취소하면_로그인_화면에_이유를_남긴다(google):
    client = TestClient(app, client=IP)
    start = client.get("/admin/auth/google/start", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    callback = client.get(
        "/admin/auth/google/callback", params={"error": "access_denied", "state": state}, follow_redirects=False
    )
    assert callback.headers["location"] == "/login?error=GOOGLE_LOGIN_FAILED"


def test_비밀번호_계정과_이메일이_겹치면_자동으로_잇지_않는다(google):
    _signup(TestClient(app, client=IP), email="lee.young+news@gmail.com")
    callback = _google_login(TestClient(app, client=IP), google, _identity())
    assert callback.headers["location"] == "/login?error=EMAIL_TAKEN"
    assert _count("select count(*) from admin_user where google_sub is not null") == 0


def test_구글이_이메일을_확인하지_않은_계정은_받지_않는다(google):
    callback = _google_login(TestClient(app, client=IP), google, _identity(verified=False))
    assert callback.headers["location"] == "/login?error=GOOGLE_EMAIL_UNVERIFIED"


def test_정지된_구글_계정은_들어올_수_없다(google):
    _google_login(TestClient(app, client=IP), google, _identity())
    ops = TestClient(app, client=IP)
    ops.post("/admin/auth/login", json={"username": "ops", "password": PASSWORD})
    ops.patch("/admin/users/lee.young.news/status", json={"active": False})
    callback = _google_login(TestClient(app, client=IP), google, _identity())
    assert callback.headers["location"] == "/login?error=INVALID_CREDENTIALS"


def test_next가_외부_주소면_첫_화면으로_돌린다(google):
    callback = _google_login(TestClient(app, client=IP), google, _identity(), next_path="//evil.example/x")
    assert callback.headers["location"] == "/"


def test_구글_전용_계정은_비밀번호로_로그인할_수_없다(google):
    _google_login(TestClient(app, client=IP), google, _identity())
    response = TestClient(app, client=IP).post(
        "/admin/auth/login", json={"username": "lee.young.news", "password": PASSWORD}
    )
    assert response.status_code == 401


def test_구글_전용_계정은_현재_비밀번호_없이_비밀번호를_처음_설정하고_그_비밀번호로도_들어온다(google):
    client = TestClient(app, client=IP)
    _google_login(client, google, _identity())
    assert client.post("/admin/auth/password", json={"new_password": PASSWORD}).status_code == 204
    assert client.get("/admin/auth/me").status_code == 200
    login = TestClient(app, client=IP).post("/admin/auth/login", json={"username": "lee.young.news", "password": PASSWORD})
    assert login.status_code == 200
    assert _count("select count(*) from admin_audit where action = 'password.change' and detail = '처음 설정'") == 1


# ── CLI ────────────────────────────────────────────────


def test_CLI로_등급을_바꾸면_이메일과_구글_연결은_그대로다(google):
    _google_login(TestClient(app, client=IP), google, _identity())
    principal = get_admin_user_use_case().set_role("lee.young.news", "operator")
    assert (principal.role, principal.can_operate) == ("operator", True)
    with session_scope() as session:
        row = session.execute(text("select email, google_sub from admin_user where username = 'lee.young.news'")).one()
    assert tuple(row) == ("lee.young+news@gmail.com", "g-1")


def test_CLI_비밀번호_재설정도_이메일을_지우지_않는다():
    _signup(TestClient(app, client=IP))
    get_admin_user_use_case().upsert("kim", "another-long-password", "operator")
    assert _count("select count(*) from admin_user where username = 'kim' and email = 'kim@example.com'") == 1


# ── 구글 어댑터 (HTTP 경계만 가짜) ───────────────────────


def _id_token(claims: dict) -> str:
    encode = lambda part: base64.urlsafe_b64encode(json.dumps(part).encode()).rstrip(b"=").decode()  # noqa: E731
    return f"{encode({'alg': 'RS256'})}.{encode(claims)}.signature"


def _adapter(status: int, claims: dict, now: float = 1_000.0) -> GoogleIdentityAdapter:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://oauth2.googleapis.com/token"
        form = parse_qs(request.content.decode())
        assert form["code_verifier"] == ["verifier"]
        assert form["grant_type"] == ["authorization_code"]
        return httpx.Response(status, json={"id_token": _id_token(claims)})

    return GoogleIdentityAdapter(
        client_id="client-1",
        client_secret="secret-1",
        redirect_uri="http://localhost:3200/api/backend/admin/auth/google/callback",
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=lambda: now,
    )


VALID = {
    "iss": "https://accounts.google.com", "aud": "client-1", "exp": 2_000, "sub": "g-9",
    "email": "park@gmail.com", "email_verified": True,
}


def test_구글_어댑터는_토큰의_발급자_대상_만료를_확인하고_신원을_꺼낸다():
    assert _adapter(200, VALID).exchange("code", "verifier") == GoogleIdentityDto(
        sub="g-9", email="park@gmail.com", email_verified=True
    )


@pytest.mark.parametrize(
    ("status", "claims"),
    [
        (400, VALID),
        (200, {**VALID, "aud": "someone-else"}),
        (200, {**VALID, "iss": "https://evil.example"}),
        (200, {**VALID, "exp": 999}),
        (200, {k: v for k, v in VALID.items() if k != "sub"}),
    ],
)
def test_구글_어댑터는_믿을_수_없는_응답이면_None(status, claims):
    assert _adapter(status, claims).exchange("code", "verifier") is None


def test_구글_어댑터는_클라이언트_ID와_비밀이_있어야_설정된_것이다():
    assert _adapter(200, VALID).is_configured()
    assert not GoogleIdentityAdapter(client_id="", client_secret="", redirect_uri="x").is_configured()


def test_구글_인증_주소는_리디렉트_URI와_범위를_싣는다():
    query = parse_qs(urlparse(_adapter(200, VALID).authorization_url("state-1", "challenge-1")).query)
    assert query["client_id"] == ["client-1"]
    assert query["redirect_uri"] == ["http://localhost:3200/api/backend/admin/auth/google/callback"]
    assert query["scope"] == ["openid email profile"]
    assert query["response_type"] == ["code"]
    assert (query["state"], query["code_challenge"], query["code_challenge_method"]) == (
        ["state-1"], ["challenge-1"], ["S256"],
    )
