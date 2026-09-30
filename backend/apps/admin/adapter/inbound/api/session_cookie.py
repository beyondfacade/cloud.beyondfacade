from datetime import datetime

from fastapi import Response

from core.matrix.grid_keymaker_secret_manager import get_settings

SESSION_COOKIE = "metabole_admin"


def set_session_cookie(response: Response, token: str, expires_at: datetime) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        expires=expires_at,
        httponly=True,
        samesite="lax",
        secure=get_settings().admin_cookie_secure,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
