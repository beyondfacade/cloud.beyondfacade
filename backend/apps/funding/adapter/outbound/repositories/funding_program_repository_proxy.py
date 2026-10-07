"""Proxy (GoF) — 미만료 공고 전량(`list_open_all`) 캐시.

공고는 하루 1회(05:10 크론, 별도 프로세스 CLI)만 바뀐다. 그 프로세스는 API 프로세스의 캐시를
지울 수 없으므로 TTL로 따라간다(최대 TTL만큼 늦게 반영). 마감 판정(`is_past_deadline(today)`)은
인터랙터·도메인이 요청 시각 기준으로 하므로 캐시된 엔티티라도 날짜가 바뀌면 마감 공고는 맞게 빠진다.
"""

import threading
import time
from collections.abc import Callable
from datetime import date

from apps.funding.app.ports.output.funding_program_port import FundingProgramRepositoryPort
from apps.funding.domain.entities.funding_program_entity import FundingProgram

LIST_OPEN_ALL_TTL_SECONDS = 600  # 10분


class CachingFundingProgramRepositoryProxy(FundingProgramRepositoryPort):
    def __init__(
        self,
        inner: FundingProgramRepositoryPort,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner = inner
        self._clock = clock
        self._lock = threading.Lock()  # 동기 라우터는 스레드풀 — 만료 순간 여러 요청이 DB를 동시에 읽지 않게
        self._programs: list[FundingProgram] | None = None
        self._loaded_at = 0.0

    def upsert(self, programs: list[FundingProgram]) -> tuple[int, int]:
        return self._inner.upsert(programs)

    def refresh_expirations(self, today: date) -> int:
        return self._inner.refresh_expirations(today)

    def list_open(self, limit: int) -> list[FundingProgram]:
        return self._inner.list_open(limit)

    def list_open_all(self) -> list[FundingProgram]:
        with self._lock:
            if self._programs is None or self._clock() - self._loaded_at >= LIST_OPEN_ALL_TTL_SECONDS:
                self._programs = self._inner.list_open_all()
                self._loaded_at = self._clock()
            # 얕은 복사(참조 1.5천 개, 수 µs)로 호출자가 캐시 리스트를 바꾸지 못하게 한다. 엔티티는 공유 —
            # 도메인·인터랙터는 엔티티를 읽기만 한다.
            return list(self._programs)
