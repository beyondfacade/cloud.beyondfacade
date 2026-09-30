"""Proxy (GoF) — 조치 단어별 최신 기사 캐시. 리포트마다 외부 검색 API를 부르지 않도록 단어마다 잠깐 보관한다.
리포트 사실 수집이 스레드로 동시에 부르므로 잠근다.
"""

import threading
from collections.abc import Callable
from datetime import datetime, timedelta

from apps.shock.app.ports.output.event_analog_port import RecentNewsPort
from apps.shock.domain.value_objects.news_headline import NewsHeadline


class CachingRecentNewsGateway(RecentNewsPort):
    def __init__(
        self,
        inner: RecentNewsPort,
        ttl: timedelta = timedelta(hours=1),
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._inner = inner
        self._ttl = ttl
        self._now = now
        self._lock = threading.Lock()
        self._cached: dict[str, tuple[datetime, list[NewsHeadline]]] = {}

    def latest(self, keyword: str) -> list[NewsHeadline]:
        with self._lock:
            now = self._now()
            hit = self._cached.get(keyword)
            if hit is None or now - hit[0] >= self._ttl:
                hit = (now, self._inner.latest(keyword))
                self._cached[keyword] = hit
            return hit[1]
