"""점포 적재 인터랙터 — 원천 읽기 → region 해석 → 멱등 업서트 (매출 인터랙터와 동일 절차)."""

from dataclasses import replace
from pathlib import Path

from apps.commerce.app.dtos.region_commerce_sales_dto import CommerceIngestResultDto
from apps.commerce.app.ports.input.region_commerce_store_use_case import (
    RegionCommerceStoreIngestUseCase,
)
from apps.commerce.app.ports.output.region_catalog_port import RegionCatalogPort
from apps.commerce.app.ports.output.region_commerce_store_port import (
    RegionCommerceStoreGatewayPort,
    RegionCommerceStoreRepositoryPort,
)


class RegionCommerceStoreIngestInteractor(RegionCommerceStoreIngestUseCase):
    def __init__(
        self,
        repository: RegionCommerceStoreRepositoryPort,
        gateway: RegionCommerceStoreGatewayPort,
        region_catalog: RegionCatalogPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._region_catalog = region_catalog

    def ingest(self, paths: list[Path]) -> CommerceIngestResultDto:
        region_by_adstrd = self._region_catalog.region_code_by_adstrd()
        processed = resolved = 0
        for path in paths:
            rows = [
                replace(row, region_code=region_by_adstrd.get(row.adstrd_code))
                for row in self._gateway.fetch_stores(path)
            ]
            processed += self._repository.upsert(rows)
            resolved += sum(1 for row in rows if row.region_code is not None)
        return CommerceIngestResultDto(
            processed=processed,
            region_resolved=resolved,
            region_unresolved=processed - resolved,
        )
