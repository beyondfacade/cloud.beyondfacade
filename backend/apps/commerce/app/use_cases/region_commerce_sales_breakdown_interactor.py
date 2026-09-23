"""분해 적재 인터랙터 — 원천 스트림 → region 해석 → 청크 단위 멱등 업서트.

매출·점포 인터랙터와 다른 점은 파일 전체를 리스트로 받지 않는다는 것뿐이다. 789만 행이라
게이트웨이가 흘려보내는 대로 CHUNK_SIZE만큼 모아 업서트하고 버린다 — 상주 메모리가 청크
하나로 묶이고, 트랜잭션도 청크 단위로 끊긴다(리포지토리 호출 1회 = 커밋 1회).
"""

from collections.abc import Iterator
from dataclasses import replace
from itertools import islice
from pathlib import Path

from apps.commerce.app.dtos.region_commerce_sales_breakdown_dto import CommerceIngestResultDto
from apps.commerce.app.ports.input.region_commerce_sales_breakdown_use_case import (
    RegionCommerceSalesBreakdownIngestUseCase,
)
from apps.commerce.app.ports.output.region_catalog_port import RegionCatalogPort
from apps.commerce.app.ports.output.region_commerce_sales_breakdown_port import (
    RegionCommerceSalesBreakdownGatewayPort,
    RegionCommerceSalesBreakdownRepositoryPort,
)
from apps.commerce.domain.entities.region_commerce_sales_breakdown_entity import (
    RegionCommerceSalesBreakdown,
)

CHUNK_SIZE = 40_000  # 커밋 1회당 행 수 — 상주 메모리와 트랜잭션 크기를 동시에 묶는 값


def _chunks(
    rows: Iterator[RegionCommerceSalesBreakdown], size: int
) -> Iterator[list[RegionCommerceSalesBreakdown]]:
    while chunk := list(islice(rows, size)):
        yield chunk


class RegionCommerceSalesBreakdownIngestInteractor(RegionCommerceSalesBreakdownIngestUseCase):
    def __init__(
        self,
        repository: RegionCommerceSalesBreakdownRepositoryPort,
        gateway: RegionCommerceSalesBreakdownGatewayPort,
        region_catalog: RegionCatalogPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._region_catalog = region_catalog

    def ingest(self, paths: list[Path]) -> CommerceIngestResultDto:
        region_by_adstrd = self._region_catalog.region_code_by_adstrd()
        processed = resolved = 0
        for path in paths:
            for chunk in _chunks(iter(self._gateway.fetch_breakdown(path)), CHUNK_SIZE):
                rows = [
                    replace(row, region_code=region_by_adstrd.get(row.adstrd_code))
                    for row in chunk
                ]
                processed += self._repository.upsert(rows)
                resolved += sum(1 for row in rows if row.region_code is not None)
        return CommerceIngestResultDto(
            processed=processed,
            region_resolved=resolved,
            region_unresolved=processed - resolved,
        )
