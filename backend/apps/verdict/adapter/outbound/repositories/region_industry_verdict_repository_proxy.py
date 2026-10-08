"""Proxy (GoF) — 업종별 전 행정동 판정(`list_by_industry`) 캐시.

판정은 매일 새벽 배치 CLI(`build_verdicts`, 별도 프로세스)만 바꾼다. 그 프로세스는 API 프로세스의 캐시를
지울 수 없으므로 TTL로 따라간다(최대 TTL만큼 늦게 반영). 같은 프로세스 안의 쓰기(배치·백테스트 CLI도 같은
배선을 쓴다)는 위임한 뒤 캐시를 모두 비운다.
"""

import threading
import time
from collections.abc import Callable, Iterable

from apps.verdict.app.ports.output.region_industry_verdict_port import RegionIndustryVerdictRepositoryPort
from apps.verdict.domain.entities.region_industry_verdict_entity import RegionIndustryVerdict

LIST_BY_INDUSTRY_TTL_SECONDS = 600  # 10분


class CachingRegionIndustryVerdictRepositoryProxy(RegionIndustryVerdictRepositoryPort):
    def __init__(
        self,
        inner: RegionIndustryVerdictRepositoryPort,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner = inner
        self._clock = clock
        self._lock = threading.Lock()  # 동기 라우터는 스레드풀 — 만료 순간 여러 요청이 DB를 동시에 읽지 않게
        self._by_industry: dict[str, tuple[float, list[RegionIndustryVerdict]]] = {}

    def upsert(self, verdicts: list[RegionIndustryVerdict]) -> int:
        processed = self._inner.upsert(verdicts)
        self._invalidate()
        return processed

    def delete_other_industries(self, keep_industry_ids: Iterable[str]) -> int:
        deleted = self._inner.delete_other_industries(keep_industry_ids)
        self._invalidate()
        return deleted

    def list_by_region(self, region_code: str) -> list[RegionIndustryVerdict]:
        return self._inner.list_by_region(region_code)

    def find(self, region_code: str, industry_id: str) -> RegionIndustryVerdict | None:
        return self._inner.find(region_code, industry_id)

    def list_by_industry(self, industry_id: str) -> list[RegionIndustryVerdict]:
        with self._lock:
            cached = self._by_industry.get(industry_id)
            if cached is None or self._clock() - cached[0] >= LIST_BY_INDUSTRY_TTL_SECONDS:
                cached = (self._clock(), self._inner.list_by_industry(industry_id))
                self._by_industry[industry_id] = cached
            # 얕은 복사로 호출자가 캐시 리스트를 바꾸지 못하게 한다. 엔티티는 frozen이라 공유한다.
            return list(cached[1])

    def _invalidate(self) -> None:
        with self._lock:
            self._by_industry.clear()
