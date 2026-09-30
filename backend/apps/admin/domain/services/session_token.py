import hashlib
import secrets
from datetime import timedelta

SESSION_TTL = timedelta(hours=12)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_session_token() -> tuple[str, str]:
    """(쿠키에 넣을 원문, DB에 넣을 해시)."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)
