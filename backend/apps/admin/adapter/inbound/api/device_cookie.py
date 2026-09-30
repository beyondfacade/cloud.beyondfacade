"""디바이스 쿠키 — 브라우저마다 한 번 발급하는 무작위 ID. 인증 수단이 아니라 목록(화이트·블랙) 대상 식별용이다.

보안 미들웨어가 관리자 경로 요청에서 쿠키를 읽고, 없거나 형식이 틀리면 새 ID를 만들어 scope["state"]에 둔다.
라우터는 client_from_scope로 같은 값을 읽는다 — 첫 요청에도 이벤트에 디바이스가 남는다.
"""

from starlette.requests import cookie_parser
from starlette.responses import Response
from starlette.types import Scope

from apps.admin.adapter.inbound.api.client_ip import client_ip_from_scope
from apps.admin.domain.entities.client_entity import Client
from apps.admin.domain.services.device_id import is_device_id, new_device_id
from core.matrix.grid_keymaker_secret_manager import get_settings

DEVICE_COOKIE = "metabole_device"
_MAX_AGE = 400 * 24 * 3600  # 브라우저가 허용하는 최대 수명(400일)
_STATE_KEY = "device_id"


def _header(scope: Scope, name: bytes) -> str | None:
    value = dict(scope.get("headers") or []).get(name)
    return value.decode("latin-1") if value else None


def ensure_device_id(scope: Scope) -> str | None:
    """요청의 디바이스 ID를 scope에 고정한다. 새로 만들었으면 그 ID를, 이미 있었으면 None을 돌려준다."""
    current = cookie_parser(_header(scope, b"cookie") or "").get(DEVICE_COOKIE)
    issued = None if is_device_id(current) else new_device_id()
    scope.setdefault("state", {})[_STATE_KEY] = issued or current
    return issued


def device_cookie_header(device_id: str) -> tuple[bytes, bytes]:
    response = Response()
    response.set_cookie(
        DEVICE_COOKIE,
        device_id,
        max_age=_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=get_settings().admin_cookie_secure,
        path="/",
    )
    return next((k, v) for k, v in response.raw_headers if k == b"set-cookie")


def client_from_scope(scope: Scope) -> Client:
    device_id = scope.get("state", {}).get(_STATE_KEY)
    if device_id is None:
        current = cookie_parser(_header(scope, b"cookie") or "").get(DEVICE_COOKIE)
        device_id = current if is_device_id(current) else None
    return Client(ip=client_ip_from_scope(scope), device_id=device_id, user_agent=_header(scope, b"user-agent"))
