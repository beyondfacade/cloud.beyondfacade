"""보안 미들웨어 (순수 ASGI — SSE 스트림을 버퍼링하지 않는다).

- 차단 IP의 관리자 경로(/admin/*) 요청을 403으로 끊는다. 공개 경로는 막지 않는다.
- 5xx·스캐너 경로 응답을 보안 이벤트로 남긴다.
- 로그인 실패·스캐너 탐색 응답 뒤에 자동 방어 규칙을 검사해, 임계치에 닿은 IP를 기한부로 차단한다.
기록·조회 실패는 요청을 깨뜨리지 않는다 — 로그만 남긴다.
"""

import logging
from collections.abc import Callable

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from apps.admin.adapter.inbound.api.client_ip import client_ip_from_scope
from apps.admin.adapter.inbound.api.error_handlers import error_body
from apps.admin.app.ports.input.access_event_use_case import AccessEventUseCase
from apps.admin.app.ports.input.ip_block_use_case import IpBlockUseCase
from apps.admin.dependencies.admin_dependencies import get_access_event_use_case, get_ip_block_use_case
from apps.admin.domain.entities.access_event_entity import AccessEventKind
from apps.admin.domain.services.auto_block_rules import triggers_auto_block
from apps.admin.domain.services.response_classifier import response_event_kind

LOGGER = logging.getLogger("beyondfacade.admin.security")
_PROTECTED_PREFIX = "/admin"


class SecurityMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        ip_blocks: Callable[[], IpBlockUseCase] = get_ip_block_use_case,
        events: Callable[[], AccessEventUseCase] = get_access_event_use_case,
    ) -> None:
        self.app = app
        self._ip_blocks = ip_blocks
        self._events = events

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path, method = scope["path"], scope["method"]
        ip = client_ip_from_scope(scope)
        if path.startswith(_PROTECTED_PREFIX) and await run_in_threadpool(self._is_blocked, ip):
            await self._record(AccessEventKind.BLOCKED_REQUEST, ip, method, path, 403)
            response = JSONResponse(error_body("IP_BLOCKED", "차단된 IP입니다."), status_code=403)
            await response(scope, receive, send)
            return

        status = 500

        async def capture_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, capture_status)
        except Exception:
            await self._record(AccessEventKind.SERVER_ERROR, ip, method, path, 500)
            raise
        kind = response_event_kind(status, path)
        if kind is not None:
            await self._record(kind, ip, method, path, status)
        if triggers_auto_block(kind, method, path, status):
            await run_in_threadpool(self._enforce_auto_defense, ip)

    def _enforce_auto_defense(self, ip: str | None) -> None:
        try:
            self._ip_blocks().enforce_auto_defense(ip)
        except Exception:
            LOGGER.exception("자동 방어 판정 실패 — 이번 요청은 차단 없이 넘긴다")

    def _is_blocked(self, ip: str | None) -> bool:
        try:
            return self._ip_blocks().is_blocked(ip)
        except Exception:
            LOGGER.exception("IP 차단 조회 실패 — 차단 없이 통과시킨다")
            return False

    async def _record(self, kind: AccessEventKind, ip: str | None, method: str, path: str, status: int) -> None:
        try:
            await run_in_threadpool(self._events().record, kind, ip, method, path, status)
        except Exception:
            LOGGER.exception("보안 이벤트 기록 실패: %s %s", kind, path)
