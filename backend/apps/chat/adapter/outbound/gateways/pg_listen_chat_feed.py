"""Driven Adapter — 프로세스마다 LISTEN 연결 하나를 열고, 받은 이벤트를 접속자별 큐로 나눠 준다."""

import asyncio
import logging
from collections.abc import Callable

import psycopg

from apps.chat.adapter.outbound.gateways.chat_event_codec import CHANNEL, decode
from apps.chat.app.dtos.chat_message_dto import ChatEventDto
from apps.chat.app.ports.output.chat_message_port import ChatEventFeedPort, ChatSubscription

logger = logging.getLogger(__name__)

QUEUE_SIZE = 200
MAX_RECONNECT_DELAY = 30.0


class _QueueSubscription(ChatSubscription):
    def __init__(self, on_close: Callable[["_QueueSubscription"], None]) -> None:
        self._queue: asyncio.Queue[ChatEventDto] = asyncio.Queue(maxsize=QUEUE_SIZE)
        self._on_close = on_close

    def push(self, event: ChatEventDto) -> None:
        if not self._queue.full():  # 못 따라오는 접속자 때문에 다른 접속자가 밀리지 않게 버린다 — 재접속하면 따라잡는다
            self._queue.put_nowait(event)

    async def next(self, timeout: float) -> ChatEventDto | None:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout)
        except TimeoutError:
            return None

    def close(self) -> None:
        self._on_close(self)


class PgListenChatFeed(ChatEventFeedPort):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._subscribers: set[_QueueSubscription] = set()
        self._task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def subscribe(self) -> ChatSubscription:
        self._ensure_listening()
        subscription = _QueueSubscription(self._subscribers.discard)
        self._subscribers.add(subscription)
        return subscription

    def _ensure_listening(self) -> None:
        loop = asyncio.get_running_loop()
        if self._task is None or self._task.done() or self._loop is not loop:
            self._loop = loop
            self._task = loop.create_task(self._listen())

    async def _listen(self) -> None:
        delay = 1.0
        while True:
            try:
                async with await psycopg.AsyncConnection.connect(self._dsn, autocommit=True) as connection:
                    await connection.execute(f"LISTEN {CHANNEL}")
                    delay = 1.0
                    async for notify in connection.notifies():
                        self._dispatch(notify.payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("채팅 LISTEN 연결이 끊겼다 — %.0f초 뒤 다시 연결", delay, exc_info=True)
                await asyncio.sleep(delay)
                delay = min(delay * 2, MAX_RECONNECT_DELAY)

    def _dispatch(self, payload: str) -> None:
        try:
            event = decode(payload)
        except (ValueError, KeyError, TypeError):
            logger.warning("읽을 수 없는 채팅 이벤트를 버렸다")
            return
        for subscription in list(self._subscribers):
            subscription.push(event)
