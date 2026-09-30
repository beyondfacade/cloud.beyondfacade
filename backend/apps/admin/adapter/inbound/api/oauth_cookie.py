"""구글 로그인 왕복 동안만 사는 쿠키 — state·PKCE verifier·돌아갈 경로를 브라우저에 맡긴다 (서버 저장소 없음).

SameSite=Lax — 구글에서 돌아오는 최상위 GET 이동에는 실리고, 다른 사이트의 하위 요청에는 실리지 않는다.
"""

import re
from dataclasses import dataclass
from urllib.parse import quote, unquote

from fastapi import Request, Response

from core.matrix.grid_keymaker_secret_manager import get_settings

OAUTH_COOKIE = "metabole_oauth"
OAUTH_TTL_SECONDS = 600
_SAFE_NEXT = re.compile(r"^/(?![/\\])[^\s\\]*$")


@dataclass(frozen=True)
class OAuthHandshake:
    state: str
    code_verifier: str
    next_path: str


def safe_next(next_path: str | None) -> str:
    """같은 사이트 안의 경로만 — //host, /\\host 같은 외부 이동은 첫 화면으로."""
    return next_path if next_path and _SAFE_NEXT.fullmatch(next_path) else "/"


def set_oauth_cookie(response: Response, handshake: OAuthHandshake) -> None:
    value = f"{handshake.state}.{handshake.code_verifier}.{quote(handshake.next_path, safe='')}"
    response.set_cookie(
        OAUTH_COOKIE,
        value,
        max_age=OAUTH_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=get_settings().admin_cookie_secure,
        path="/",
    )


def read_oauth_cookie(request: Request) -> OAuthHandshake | None:
    parts = request.cookies.get(OAUTH_COOKIE, "").split(".", 2)
    if len(parts) != 3:
        return None
    state, verifier, next_path = parts
    return OAuthHandshake(state=state, code_verifier=verifier, next_path=safe_next(unquote(next_path)))


def clear_oauth_cookie(response: Response) -> None:
    response.delete_cookie(OAUTH_COOKIE, path="/")
