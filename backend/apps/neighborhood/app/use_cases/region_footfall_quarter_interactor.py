"""region_footfall_quarter 적재 인터랙터 — 원천 스트림 → region 해석 → 청크 단위 멱등 업서트.

절차 자체는 `region_quarter_ingest.ingest_with_region`에 한 벌만 둔다 (7개 공통).
"""

from pathlib import Path

from apps.neighborhood.app.dtos.region_footfall_quarter_dto import NeighborhoodIngestResultDto
from apps.neighborhood.app.ports.input.region_footfall_quarter_use_case import (
    RegionFootfallQuarterIngestUseCase,
)
from apps.neighborhood.app.ports.output.region_catalog_port import RegionCatalogPort
from apps.neighborhood.app.ports.output.region_footfall_quarter_port import (
    RegionFootfallQuarterGatewayPort,
    RegionFootfallQuarterRepositoryPort,
)
from apps.neighborhood.app.use_cases.region_quarter_ingest import ingest_with_region


class RegionFootfallQuarterIngestInteractor(RegionFootfallQuarterIngestUseCase):
    def __init__(
        self,
        repository: RegionFootfallQuarterRepositoryPort,
        gateway: RegionFootfallQuarterGatewayPort,
        region_catalog: RegionCatalogPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._region_catalog = region_catalog

    def ingest(self, paths: list[Path]) -> NeighborhoodIngestResultDto:
        return ingest_with_region(
            paths, self._gateway.fetch_footfall, self._repository, self._region_catalog
        )
