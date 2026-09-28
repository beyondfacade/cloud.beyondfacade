from collections.abc import Callable
from dataclasses import asdict
from datetime import date, datetime, timedelta
from itertools import batched

from apps.store.app.dtos.store_dto import IngestTarget, StoreDto
from apps.store.app.ports.input.store_use_case import StoreUseCase
from apps.store.app.ports.output.store_port import (
    IndustryCatalogPort,
    StorePermitGatewayPort,
    StoreRepositoryPort,
)
from apps.store.domain.entities.store_entity import Store
from apps.store.domain.errors import IndustryNotFoundError, StoreStatusNotFoundError

_CHUNK_SIZE = 500
_CLOSED_WINDOW_DAYS = 730  # 최근 2년 (설계서 §6-1)

# status → 조회 전략. 새 상태는 항목 추가로 끝난다.
_LISTERS: dict[str, Callable[[StoreRepositoryPort, str, str], list[Store]]] = {
    "open": lambda repo, region, industry: repo.list_open(region, industry),
    "closed": lambda repo, region, industry: repo.list_closed_since(
        region, industry, date.today() - timedelta(days=_CLOSED_WINDOW_DAYS)
    ),
}


class StoreInteractor(StoreUseCase):
    def __init__(
        self,
        repository: StoreRepositoryPort,
        gateway: StorePermitGatewayPort,
        # 수집 전용 호출부(store_collector·기존 테스트)가 조회 포트 없이 구성하도록 기본 None
        industry_catalog: IndustryCatalogPort | None = None,
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._industry_catalog = industry_catalog

    def myself(self) -> StoreDto:
        return StoreDto(
            store_id="myself",
            name="store BC 배선 검증",
            industry_id="cafe",
            district_code="11110",
            open_date=date(2026, 8, 25),
            close_date=None,
            status_code="01",
            status_name="영업",
            lat=37.5,
            lng=127.0,
            source_updated_at=datetime(2026, 8, 25),
        )

    def ingest(self, targets: list[IngestTarget], *, full: bool = False) -> int:
        processed = 0
        for target in targets:
            cursor = (
                None
                if full
                else self._repository.latest_source_updated_at(
                    list(target.industry_ids) or [target.industry_id], target.district_code
                )
            )
            stream = self._gateway.iter_stores(target, updated_since=cursor)
            for chunk in batched(stream, _CHUNK_SIZE):
                processed += self._repository.upsert(list(chunk))
        return processed

    def list_open_stores(self, region_code: str, industry_id: str) -> list[StoreDto]:
        if not self._industry_catalog.exists(industry_id):
            raise IndustryNotFoundError(industry_id)
        return [
            StoreDto(**asdict(store))
            for store in self._repository.list_open(region_code, industry_id)
        ]

    def list_stores(self, region_code: str, industry_id: str, status: str) -> list[StoreDto]:
        lister = _LISTERS.get(status)
        if lister is None:
            raise StoreStatusNotFoundError(status)
        if not self._industry_catalog.exists(industry_id):
            raise IndustryNotFoundError(industry_id)
        return [StoreDto(**asdict(store)) for store in lister(self._repository, region_code, industry_id)]
