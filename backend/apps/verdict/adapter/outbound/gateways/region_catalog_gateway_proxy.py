"""Proxy (GoF) — 전 행정동 이름 + 최신 분기 동네 유형(`regions`) 캐시.

동 목록은 거의 안 바뀌고 동네 유형은 분기 단위로 적재(별도 프로세스 CLI)되므로 TTL로 따라간다.
"""

import threading
import time
from collections.abc import Callable

from apps.verdict.app.dtos.region_industry_verdict_dto import RegionInfo
from apps.verdict.app.ports.output.region_industry_verdict_port import RegionCatalogPort

REGIONS_TTL_SECONDS = 600  # 10분


class CachingRegionCatalogGatewayProxy(RegionCatalogPort):
    def __init__(self, inner: RegionCatalogPort, clock: Callable[[], float] = time.monotonic) -> None:
        self._inner = inner
        self._clock = clock
        self._lock = threading.Lock()
        self._regions: list[RegionInfo] | None = None
        self._loaded_at = 0.0

    def regions(self) -> list[RegionInfo]:
        with self._lock:
            if self._regions is None or self._clock() - self._loaded_at >= REGIONS_TTL_SECONDS:
                self._regions = self._inner.regions()
                self._loaded_at = self._clock()
            return list(self._regions)  # 얕은 복사 — RegionInfo는 frozen
