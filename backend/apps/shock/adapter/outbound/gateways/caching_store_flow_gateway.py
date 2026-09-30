"""Proxy (GoF) — 월 개폐업 흐름 캐시. 인허가 원천은 하루 한 번 갱신되고 집계는 서울 전체라
요청마다 88만 행을 다시 묶을 이유가 없다. 리포트 사실 수집이 스레드로 동시에 부르므로 잠근다.
"""

import threading
from collections.abc import Callable
from datetime import datetime, timedelta

from apps.shock.app.ports.output.event_analog_port import StoreFlowPort
from apps.shock.domain.services.industry_flows import IndustryFlows


class CachingStoreFlowGateway(StoreFlowPort):
    def __init__(
        self,
        inner: StoreFlowPort,
        ttl: timedelta = timedelta(hours=6),
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._inner = inner
        self._ttl = ttl
        self._now = now
        self._lock = threading.Lock()
        self._cached: list[IndustryFlows] | None = None
        self._fetched_at: datetime | None = None

    def monthly_flows(self) -> list[IndustryFlows]:
        with self._lock:
            now = self._now()
            if self._cached is None or self._fetched_at is None or now - self._fetched_at >= self._ttl:
                self._cached = self._inner.monthly_flows()
                self._fetched_at = now
            return self._cached
