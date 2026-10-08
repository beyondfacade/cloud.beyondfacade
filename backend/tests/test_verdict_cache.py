"""판정·동 목록 캐싱 Proxy — TTL 안에서는 DB를 한 번만 읽고, 판정 쓰기 뒤에는 다시 읽는다."""

from apps.verdict.adapter.outbound.gateways.region_catalog_gateway_proxy import (
    REGIONS_TTL_SECONDS,
    CachingRegionCatalogGatewayProxy,
)
from apps.verdict.adapter.outbound.repositories.region_industry_verdict_repository_proxy import (
    LIST_BY_INDUSTRY_TTL_SECONDS,
    CachingRegionIndustryVerdictRepositoryProxy,
)
from apps.verdict.app.dtos.region_industry_verdict_dto import RegionInfo
from apps.verdict.app.ports.output.region_industry_verdict_port import (
    RegionCatalogPort,
    RegionIndustryVerdictRepositoryPort,
)


class _CountingRepository(RegionIndustryVerdictRepositoryPort):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def upsert(self, verdicts):
        self.calls.append("upsert")
        return len(verdicts)

    def list_by_industry(self, industry_id):
        self.calls.append(f"list_by_industry:{industry_id}")
        return []

    def list_by_region(self, region_code):
        self.calls.append("list_by_region")
        return []

    def find(self, region_code, industry_id):
        self.calls.append("find")
        return None

    def delete_other_industries(self, keep_industry_ids):
        self.calls.append("delete_other_industries")
        return 0


class _CountingRegionCatalog(RegionCatalogPort):
    def __init__(self) -> None:
        self.calls = 0

    def regions(self):
        self.calls += 1
        return [RegionInfo("1144066000", "서교동", "office")]


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_TTL_안에서_같은_업종은_한_번만_읽는다():
    inner, clock = _CountingRepository(), _Clock()
    proxy = CachingRegionIndustryVerdictRepositoryProxy(inner, clock=clock)

    proxy.list_by_industry("cafe")
    clock.now += LIST_BY_INDUSTRY_TTL_SECONDS - 1
    proxy.list_by_industry("cafe")

    assert inner.calls == ["list_by_industry:cafe"]


def test_업종이_다르면_따로_읽는다():
    inner = _CountingRepository()
    proxy = CachingRegionIndustryVerdictRepositoryProxy(inner, clock=_Clock())

    proxy.list_by_industry("cafe")
    proxy.list_by_industry("chicken")

    assert inner.calls == ["list_by_industry:cafe", "list_by_industry:chicken"]


def test_쓰기_뒤에는_다시_읽는다():
    inner = _CountingRepository()
    proxy = CachingRegionIndustryVerdictRepositoryProxy(inner, clock=_Clock())

    proxy.list_by_industry("cafe")
    proxy.upsert([])
    proxy.list_by_industry("cafe")
    proxy.delete_other_industries(["cafe"])
    proxy.list_by_industry("cafe")

    assert inner.calls == [
        "list_by_industry:cafe", "upsert", "list_by_industry:cafe", "delete_other_industries", "list_by_industry:cafe",
    ]


def test_TTL이_지나면_다시_읽는다():
    inner, clock = _CountingRepository(), _Clock()
    proxy = CachingRegionIndustryVerdictRepositoryProxy(inner, clock=clock)

    proxy.list_by_industry("cafe")
    clock.now += LIST_BY_INDUSTRY_TTL_SECONDS
    proxy.list_by_industry("cafe")

    assert inner.calls == ["list_by_industry:cafe", "list_by_industry:cafe"]


def test_동_목록은_TTL_안에서_한_번만_읽는다():
    inner, clock = _CountingRegionCatalog(), _Clock()
    proxy = CachingRegionCatalogGatewayProxy(inner, clock=clock)

    proxy.regions()
    clock.now += REGIONS_TTL_SECONDS - 1
    second = proxy.regions()

    assert inner.calls == 1
    assert [r.region_code for r in second] == ["1144066000"]
