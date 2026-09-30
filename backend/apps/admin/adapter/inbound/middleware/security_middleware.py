"""보안 미들웨어 (순수 ASGI — SSE 스트림을 버퍼링하지 않는다).

- 관리자 경로(/admin/*) 요청에 디바이스 쿠키를 붙이고(없을 때만), 차단 IP·블랙리스트 디바이스를 403으로 끊는다.
  공개 경로는 막지 않는다. 자동 차단된 IP라도 화이트리스트 IP·디바이스는 통과한다.
- 5xx·스캐너 경로 응답을 보안 이벤트로 남긴다.
- 로그인 실패·스캐너 탐색 응답 뒤에 자동 방어 규칙을 검사해, 임계치에 닿은 IP를 기한부로 차단한다.
기록·조회 실패는 요청을 깨뜨리지 않는다 — 로그만 남긴다.
"""

import logging
from collections.abc import Callable

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from apps.admin.adapter.inbound.api.device_cookie import client_from_scope, device_cookie_header, ensure_device_id
from apps.admin.adapter.inbound.api.error_handlers import error_body
from apps.admin.app.ports.input.access_event_use_case import AccessEventUseCase
from apps.admin.app.ports.input.access_rule_use_case import AccessRuleUseCase
from apps.admin.app.ports.input.ip_block_use_case import IpBlockUseCase
from apps.admin.dependencies.admin_dependencies import (
    get_access_event_use_case,
    get_access_rule_use_case,
    get_ip_block_use_case,
)
from apps.admin.domain.entities.access_event_entity import AccessEventKind
from apps.admin.domain.entities.client_entity import Client
from apps.admin.domain.services.auto_block_rules import triggers_auto_block
from apps.admin.domain.services.response_classifier import response_event_kind

LOGGER = logging.getLogger("beyondfacade.admin.security")
_PROTECTED_PREFIX = "/admin"
_BLOCKED = {"IP_BLOCKED": "차단된 IP입니다.", "DEVICE_BLOCKED": "차단된 디바이스입니다."}


class SecurityMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        ip_blocks: Callable[[], IpBlockUseCase] = get_ip_block_use_case,
        events: Callable[[], AccessEventUseCase] = get_access_event_use_case,
        access_rules: Callable[[], AccessRuleUseCase] = get_access_rule_use_case,
    ) -> None:
        self.app = app
        self._ip_blocks = ip_blocks
        self._events = events
        self._access_rules = access_rules

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path, method = scope["path"], scope["method"]
        protected = path.startswith(_PROTECTED_PREFIX)
        issued = ensure_device_id(scope) if protected else None
        client = client_from_scope(scope)
        if protected and (code := await run_in_threadpool(self._blocked_code, client)):
            await self._record(AccessEventKind.BLOCKED_REQUEST, client, method, path, 403)
            response = JSONResponse(error_body(code, _BLOCKED[code]), status_code=403)
            await response(scope, receive, send)
            return

        status = 500

        async def capture_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                if issued:
                    message["headers"] = [*message.get("headers", []), device_cookie_header(issued)]
            await send(message)

        try:
            await self.app(scope, receive, capture_status)
        except Exception:
            await self._record(AccessEventKind.SERVER_ERROR, client, method, path, 500)
            raise
        kind = response_event_kind(status, path)
        if kind is not None:
            await self._record(kind, client, method, path, status)
        if triggers_auto_block(kind, method, path, status):
            await run_in_threadpool(self._enforce_auto_defense, client)

    def _enforce_auto_defense(self, client: Client) -> None:
        try:
            self._ip_blocks().enforce_auto_defense(client)
        except Exception:
            LOGGER.exception("자동 방어 판정 실패 — 이번 요청은 차단 없이 넘긴다")

    def _blocked_code(self, client: Client) -> str | None:
        try:
            if self._ip_blocks().is_blocked(client):
                return "IP_BLOCKED"
            if self._access_rules().is_denied(client):
                return "DEVICE_BLOCKED"
        except Exception:
            LOGGER.exception("차단 목록 조회 실패 — 차단 없이 통과시킨다")
        return None

    async def _record(self, kind: AccessEventKind, client: Client, method: str, path: str, status: int) -> None:
        try:
            await run_in_threadpool(self._events().record, kind, client, method, path, status)
        except Exception:
            LOGGER.exception("보안 이벤트 기록 실패: %s %s", kind, path)
