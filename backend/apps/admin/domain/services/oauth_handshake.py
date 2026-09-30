"""OAuth 인가 코드 흐름의 일회용 값 — state(CSRF)와 PKCE(S256) verifier·challenge."""

import base64
import hashlib
import secrets


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)


def new_pkce_pair() -> tuple[str, str]:
    """(verifier, challenge) — verifier는 RFC 7636의 43~128자 범위(86자)."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
