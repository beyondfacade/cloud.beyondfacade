"""구글 OpenID Connect 어댑터 — 인가 코드 + PKCE를 토큰 엔드포인트에서 ID 토큰으로 바꾼다.

ID 토큰은 TLS로 구글 토큰 엔드포인트에서 직접 받으므로 서명 대신 iss·aud·exp를 확인한다
(OpenID Connect Core 3.1.3.7). 토큰·코드·비밀은 로그에 남기지 않는다.
"""

import base64
import binascii
import json
import logging
import time
from collections.abc import Callable
from urllib.parse import urlencode

import httpx

from apps.admin.app.dtos.google_identity_dto import GoogleIdentityDto
from apps.admin.app.ports.output.google_identity_port import GoogleIdentityPort

LOGGER = logging.getLogger("beyondfacade.admin.google")
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})
_TIMEOUT_SECONDS = 10.0


def _claims(id_token: str) -> dict | None:
    try:
        payload = id_token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError, binascii.Error):
        return None
    return claims if isinstance(claims, dict) else None


class GoogleIdentityAdapter(GoogleIdentityPort):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        http: httpx.Client | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._http = http or httpx.Client(timeout=_TIMEOUT_SECONDS)
        self._clock = clock

    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def authorization_url(self, state: str, code_challenge: str) -> str:
        query = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        return f"{AUTH_URL}?{urlencode(query)}"

    def exchange(self, code: str, code_verifier: str) -> GoogleIdentityDto | None:
        form = {
            "code": code,
            "code_verifier": code_verifier,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
        }
        try:
            response = self._http.post(TOKEN_URL, data=form)
        except httpx.HTTPError as error:
            LOGGER.warning("구글 토큰 교환 요청 실패: %s", type(error).__name__)
            return None
        if response.status_code != 200:
            LOGGER.warning("구글 토큰 교환 거절: HTTP %s", response.status_code)
            return None
        try:
            claims = _claims(str(response.json()["id_token"]))
        except (ValueError, KeyError, TypeError):
            claims = None
        if not self._trusted(claims):
            LOGGER.warning("구글 ID 토큰 검증 실패")
            return None
        return GoogleIdentityDto(
            sub=str(claims["sub"]), email=str(claims.get("email", "")), email_verified=claims.get("email_verified") is True
        )

    def _trusted(self, claims: dict | None) -> bool:
        if not claims or not claims.get("sub"):
            return False
        expires = claims.get("exp")
        return (
            claims.get("iss") in _ISSUERS
            and claims.get("aud") == self._client_id
            and isinstance(expires, int | float)
            and expires > self._clock()
        )
