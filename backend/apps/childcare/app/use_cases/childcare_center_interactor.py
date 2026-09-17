"""어린이집 시설 인터랙터 — 스냅샷 수집(자치구 단위 전량 멱등 업서트)·지도 마커 조회.

convenience 전례대로 관측과 해석을 분리한다: 소실 시설을 폐원으로 판정하지 않고
last_seen_on 정지로만 남긴다.
"""

from datetime import date

from apps.childcare.app.dtos.childcare_center_dto import ChildcareCenterDto
from apps.childcare.app.ports.input.childcare_center_use_case import (
    ChildcareCenterQueryUseCase,
    ChildcareSnapshotUseCase,
)
from apps.childcare.app.ports.output.childcare_center_port import (
    ChildcareCenterQueryRepositoryPort,
    ChildcareGatewayPort,
    ChildcareSnapshotRepositoryPort,
    RegionCatalogPort,
)
from apps.childcare.domain.errors import RegionNotFoundError


class ChildcareSnapshotInteractor(ChildcareSnapshotUseCase):
    def __init__(
        self,
        repository: ChildcareSnapshotRepositoryPort,
        gateway: ChildcareGatewayPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    def ingest(self, district_code: str, observed_on: date) -> int:
        return self._repository.upsert(self._gateway.fetch_centers(district_code), observed_on)


class ChildcareCenterQueryInteractor(ChildcareCenterQueryUseCase):
    def __init__(
        self,
        repository: ChildcareCenterQueryRepositoryPort,
        region_catalog: RegionCatalogPort,
    ) -> None:
        self._repository = repository
        self._region_catalog = region_catalog

    def myself(self) -> ChildcareCenterDto:
        return ChildcareCenterDto(
            center_id="myself",
            name="childcare BC 배선 검증",
            type_name="국공립",
            status_name="정상",
            lat=37.5,
            lng=127.0,
            base_date=date(2026, 9, 17),
            capacity=39,
            child_count=25,
            waiting_count=20,
        )

    def list_centers(self, region_code: str) -> list[ChildcareCenterDto]:
        if not self._region_catalog.exists(region_code):
            raise RegionNotFoundError(region_code)
        return [
            ChildcareCenterDto(
                center_id=center.center_id,
                name=center.name,
                type_name=center.type_name,
                status_name=center.status_name,
                lat=center.lat,
                lng=center.lng,
                base_date=center.stat.base_date,
                capacity=center.stat.capacity,
                child_count=center.stat.child_count,
                waiting_count=center.stat.waiting_count,
            )
            for center in self._repository.list_operating(region_code)
        ]
