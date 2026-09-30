"""Proxy (GoF) — 자치구별 월 개폐업 흐름 캐시. 같은 구의 리포트가 이어지면 매번 다시 묶을 이유가 없다.
구마다 따로 유효 시간을 잰다. 리포트 사실 수집이 스레드로 동시에 부르므로 잠근다.
"""

import threading
from collections.abc import Callable
from datetime import datetime, timedelta

from apps.shock.app.ports.output.event_analog_port import DistrictFlowPort
from apps.shock.domain.services.industry_flows import IndustryFlows


class CachingDistrictFlowGateway(DistrictFlowPort):
    def __init__(
        self,
        inner: DistrictFlowPort,
        ttl: timedelta = timedelta(hours=6),
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._inner = inner
        self._ttl = ttl
        self._now = now
        self._lock = threading.Lock()
        self._cached: dict[str, tuple[datetime, list[IndustryFlows]]] = {}

    def district_flows(self, district_code: str) -> list[IndustryFlows]:
        with self._lock:
            now = self._now()
            hit = self._cached.get(district_code)
            if hit is None or now - hit[0] >= self._ttl:
                hit = (now, self._inner.district_flows(district_code))
                self._cached[district_code] = hit
            return hit[1]

    def district_name(self, district_code: str) -> str | None:
        return self._inner.district_name(district_code)
