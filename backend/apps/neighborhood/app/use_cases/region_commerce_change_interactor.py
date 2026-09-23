"""region_commerce_change 적재 인터랙터 — 원천 스트림 → region 해석 → 청크 단위 멱등 업서트.

절차 자체는 `region_quarter_ingest.ingest_with_region`에 한 벌만 둔다 (7개 공통).
"""

from pathlib import Path

from apps.neighborhood.app.dtos.region_commerce_change_dto import NeighborhoodIngestResultDto
from apps.neighborhood.app.ports.input.region_commerce_change_use_case import (
    RegionCommerceChangeIngestUseCase,
)
from apps.neighborhood.app.ports.output.region_catalog_port import RegionCatalogPort
from apps.neighborhood.app.ports.output.region_commerce_change_port import (
    RegionCommerceChangeGatewayPort,
    RegionCommerceChangeRepositoryPort,
)
from apps.neighborhood.app.use_cases.region_quarter_ingest import ingest_with_region


class RegionCommerceChangeIngestInteractor(RegionCommerceChangeIngestUseCase):
    def __init__(
        self,
        repository: RegionCommerceChangeRepositoryPort,
        gateway: RegionCommerceChangeGatewayPort,
        region_catalog: RegionCatalogPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._region_catalog = region_catalog

    def ingest(self, paths: list[Path]) -> NeighborhoodIngestResultDto:
        return ingest_with_region(
            paths, self._gateway.fetch_changes, self._repository, self._region_catalog
        )
