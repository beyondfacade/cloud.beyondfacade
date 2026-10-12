"""프론트(www)와 API(api)가 다른 호스트일 때의 설정 — CORS 허용 주소·관리자 쿠키 도메인 (serverplan Phase 6-4).

기본값은 로컬 개발(같은 origin 프록시)과 같은 동작이다.
"""

import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from apps.admin.adapter.inbound.api.device_cookie import device_cookie_header
from apps.admin.adapter.inbound.api.oauth_cookie import OAuthHandshake, clear_oauth_cookie, set_oauth_cookie
from apps.admin.adapter.inbound.api.session_cookie import clear_session_cookie, set_session_cookie
from core.matrix.grid_keymaker_secret_manager import Settings, get_settings
from main import app


@pytest.fixture
def cookie_domain(monkeypatch):
    monkeypatch.setenv("COOKIE_DOMAIN", "beyondfacade.cloud")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


def test_CORS_허용_주소는_쉼표로_구분한_env에서_읽는다():
    settings = Settings(cors_allow_origins="https://www.beyondfacade.cloud, https://beyondfacade.cloud")
    assert settings.cors_origin_list == ["https://www.beyondfacade.cloud", "https://beyondfacade.cloud"]


def test_허용된_프론트의_사전_요청에는_쿠키를_실어도_된다고_답한다():
    response = TestClient(app).options(
        "/health",
        headers={"Origin": "http://localhost:3200", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3200"
    assert response.headers["access-control-allow-credentials"] == "true"


def _set_cookie_headers(response: Response) -> list[str]:
    return [v.decode() for k, v in response.raw_headers if k == b"set-cookie"]


def test_쿠키_도메인을_정하면_관리자_쿠키_3종을_그_도메인에_붙이고_지울_때도_같은_도메인을_쓴다(cookie_domain):
    from datetime import datetime, timedelta, timezone

    response = Response()
    set_session_cookie(response, "token", datetime.now(timezone.utc) + timedelta(hours=1))
    set_oauth_cookie(response, OAuthHandshake("state", "verifier", "/admin"))
    clear_session_cookie(response)
    clear_oauth_cookie(response)
    headers = _set_cookie_headers(response) + [device_cookie_header("d" * 32)[1].decode()]
    assert len(headers) == 5
    assert all("Domain=beyondfacade.cloud" in header for header in headers)
