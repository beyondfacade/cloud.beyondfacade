"""공고 목록 캐싱 Proxy — TTL 안에서는 DB를 한 번만 읽고, 나머지 메서드는 그대로 위임한다."""

from datetime import date

from apps.funding.adapter.outbound.repositories.funding_program_repository_proxy import (
    LIST_OPEN_ALL_TTL_SECONDS,
    CachingFundingProgramRepositoryProxy,
)
from apps.funding.app.ports.output.funding_program_port import FundingProgramRepositoryPort
from apps.funding.domain.entities.funding_program_entity import FundingProgram


class _CountingRepository(FundingProgramRepositoryPort):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def upsert(self, programs):
        self.calls.append("upsert")
        return (len(programs), 0)

    def refresh_expirations(self, today):
        self.calls.append("refresh_expirations")
        return 3

    def list_open(self, limit):
        self.calls.append("list_open")
        return []

    def list_open_all(self):
        self.calls.append("list_open_all")
        return [FundingProgram("p1", "bizinfo", "공고", "기관", "https://example.com/p1", "상시")]


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_TTL_안에서는_내부_리포지토리를_한_번만_읽는다():
    inner, clock = _CountingRepository(), _Clock()
    proxy = CachingFundingProgramRepositoryProxy(inner, clock=clock)

    first = proxy.list_open_all()
    clock.now += LIST_OPEN_ALL_TTL_SECONDS - 1
    second = proxy.list_open_all()

    assert inner.calls == ["list_open_all"]
    assert [p.program_id for p in second] == [p.program_id for p in first] == ["p1"]


def test_TTL이_지나면_다시_읽는다():
    inner, clock = _CountingRepository(), _Clock()
    proxy = CachingFundingProgramRepositoryProxy(inner, clock=clock)

    proxy.list_open_all()
    clock.now += LIST_OPEN_ALL_TTL_SECONDS
    proxy.list_open_all()

    assert inner.calls == ["list_open_all", "list_open_all"]


def test_list_open_all_외_메서드는_캐시_없이_위임한다():
    inner = _CountingRepository()
    proxy = CachingFundingProgramRepositoryProxy(inner, clock=_Clock())

    assert proxy.upsert([]) == (0, 0)
    assert proxy.refresh_expirations(date(2026, 10, 7)) == 3
    proxy.list_open(5)
    proxy.list_open(5)

    assert inner.calls == ["upsert", "refresh_expirations", "list_open", "list_open"]
