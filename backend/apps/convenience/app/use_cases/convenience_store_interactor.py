"""편의점 인터랙터 — 스냅샷 수집(행정동 단위 전량 멱등 업서트)·지도 마커/요약 조회.

broker 전례와 달리 폐점 추정(mark_closed)을 하지 않는다: 원천(소진공 상가정보)은
개폐업 분석에 못 쓴다(api.md §2-3). 소실은 last_seen_on이 멈추는 것으로만 기록하고
"사라짐=폐점 추정" 판정은 후속 분석의 몫으로 남긴다 — 관측과 해석의 분리.
"""

from datetime import date
from itertools import batched

from apps.convenience.app.dtos.convenience_store_dto import (
    BrandCountDto,
    ConvenienceRegionSummaryDto,
    ConvenienceStoreDto,
)
from apps.convenience.app.ports.input.convenience_store_use_case import (
    ConvenienceSnapshotUseCase,
    ConvenienceStoreQueryUseCase,
)
from apps.convenience.app.ports.output.convenience_store_port import (
    ConvenienceGatewayPort,
    ConvenienceSnapshotRepositoryPort,
    ConvenienceStoreQueryRepositoryPort,
    RegionCatalogPort,
)
from apps.convenience.domain.entities.convenience_store_entity import ConvenienceRegionSummary
from apps.convenience.domain.errors import RegionNotFoundError

_CHUNK_SIZE = 500


class ConvenienceSnapshotInteractor(ConvenienceSnapshotUseCase):
    def __init__(
        self,
        repository: ConvenienceSnapshotRepositoryPort,
        gateway: ConvenienceGatewayPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    def ingest(self, region_code: str, observed_on: date) -> int:
        processed = 0
        for chunk in batched(self._gateway.iter_stores(region_code), _CHUNK_SIZE):
            processed += self._repository.upsert(list(chunk), observed_on)
        return processed


class ConvenienceStoreQueryInteractor(ConvenienceStoreQueryUseCase):
    def __init__(
        self,
        repository: ConvenienceStoreQueryRepositoryPort,
        region_catalog: RegionCatalogPort,
    ) -> None:
        self._repository = repository
        self._region_catalog = region_catalog

    def myself(self) -> ConvenienceStoreDto:
        return ConvenienceStoreDto(
            store_id="myself",
            name="convenience BC 배선 검증",
            branch_name=None,
            brand="CU",
            lat=37.5,
            lng=127.0,
            road_address=None,
        )

    def list_stores(self, region_code: str) -> list[ConvenienceStoreDto]:
        self._require_region(region_code)
        return [
            ConvenienceStoreDto(
                store_id=store.store_id,
                name=store.name,
                branch_name=store.branch_name,
                brand=store.brand,
                lat=store.lat,
                lng=store.lng,
                road_address=store.road_address,
            )
            for store in self._repository.list_current(region_code)
            if store.lat is not None and store.lng is not None
        ]

    def summarize_region(self, region_code: str) -> ConvenienceRegionSummaryDto:
        self._require_region(region_code)
        summary = ConvenienceRegionSummary.of(region_code, self._repository.list_current(region_code))
        return ConvenienceRegionSummaryDto(
            region_code=summary.region_code,
            store_count=summary.store_count,
            brands=[BrandCountDto(brand=b.brand, count=b.count) for b in summary.brands],
            source_stdr_ym=summary.source_stdr_ym,
        )

    def _require_region(self, region_code: str) -> None:
        if not self._region_catalog.exists(region_code):
            raise RegionNotFoundError(region_code)
