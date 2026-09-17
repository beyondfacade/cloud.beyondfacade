"""어린이집 현황 인터랙터 — 행정동 최신 현황 합계 (집계 규칙은 도메인 ChildcareRegionSummary)."""

from dataclasses import asdict
from datetime import date

from apps.childcare.app.dtos.childcare_center_stat_dto import ChildcareRegionSummaryDto
from apps.childcare.app.ports.input.childcare_center_stat_use_case import (
    ChildcareCenterStatUseCase,
)
from apps.childcare.app.ports.output.childcare_center_port import RegionCatalogPort
from apps.childcare.app.ports.output.childcare_center_stat_port import (
    ChildcareCenterStatRepositoryPort,
)
from apps.childcare.domain.entities.childcare_center_stat_entity import ChildcareRegionSummary
from apps.childcare.domain.errors import RegionNotFoundError


class ChildcareCenterStatInteractor(ChildcareCenterStatUseCase):
    def __init__(
        self,
        repository: ChildcareCenterStatRepositoryPort,
        region_catalog: RegionCatalogPort,
    ) -> None:
        self._repository = repository
        self._region_catalog = region_catalog

    def myself(self) -> ChildcareRegionSummaryDto:
        return ChildcareRegionSummaryDto(
            region_code="myself",
            base_date=date(2026, 9, 17),
            center_count=1,
            capacity=39,
            child_count=25,
            occupancy_rate=0.641,
            waiting_count=20,
        )

    def summarize_region(self, region_code: str) -> ChildcareRegionSummaryDto:
        if not self._region_catalog.exists(region_code):
            raise RegionNotFoundError(region_code)
        summary = ChildcareRegionSummary.of(region_code, self._repository.list_latest(region_code))
        return ChildcareRegionSummaryDto(**asdict(summary))
