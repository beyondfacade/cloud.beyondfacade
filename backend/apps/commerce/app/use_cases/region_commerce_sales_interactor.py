"""추정매출 적재 인터랙터 — 원천 읽기 → region 해석 → 멱등 업서트.

region 해석은 8자리 키 맵을 ingest 1회당 한 번만 읽는다(설계서 §5). 미매칭 행은 버리지 않고
region_code를 NULL로 둔 채 적재한다 — 안분·추정 근거가 없기 때문이다(§3-1).
"""

from dataclasses import replace
from pathlib import Path

from apps.commerce.app.dtos.region_commerce_sales_dto import CommerceIngestResultDto
from apps.commerce.app.ports.input.region_commerce_sales_use_case import (
    RegionCommerceSalesIngestUseCase,
)
from apps.commerce.app.ports.output.region_catalog_port import RegionCatalogPort
from apps.commerce.app.ports.output.region_commerce_sales_port import (
    RegionCommerceSalesGatewayPort,
    RegionCommerceSalesRepositoryPort,
)


class RegionCommerceSalesIngestInteractor(RegionCommerceSalesIngestUseCase):
    def __init__(
        self,
        repository: RegionCommerceSalesRepositoryPort,
        gateway: RegionCommerceSalesGatewayPort,
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
                for row in self._gateway.fetch_sales(path)
            ]
            processed += self._repository.upsert(rows)
            resolved += sum(1 for row in rows if row.region_code is not None)
        return CommerceIngestResultDto(
            processed=processed,
            region_resolved=resolved,
            region_unresolved=processed - resolved,
        )
