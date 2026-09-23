"""학원·부동산 좌표 결측분 SGIS 지오코딩 인터랙터."""

from apps.store.app.ports.input.geocode_stores_use_case import (
    GeocodeResult,
    GeocodeStoresUseCase,
)
from apps.store.app.ports.output.geocoding_port import GeocodingGatewayPort
from apps.store.app.ports.output.store_geocode_port import StoreGeocodeRepositoryPort

# 중간 커밋 주기 — 장시간 실행·중단 재개 시 이미 성공분 보존
_FLUSH_EVERY = 200


class GeocodeStoresInteractor(GeocodeStoresUseCase):
    def __init__(
        self,
        repository: StoreGeocodeRepositoryPort,
        gateway: GeocodingGatewayPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    def run(
        self, industry_ids: list[str], limit: int | None = None
    ) -> GeocodeResult:
        pending = self._repository.list_pending(industry_ids, limit=limit)
        updates: list[tuple[str, float, float]] = []
        unmatched = 0
        geocoded = 0
        for store in pending:
            address = store.road_address or store.jibun_address
            if not address:
                unmatched += 1
                continue
            coords = self._gateway.geocode(address)
            if coords is None and store.jibun_address and store.road_address:
                coords = self._gateway.geocode(store.jibun_address)
            if coords is None:
                unmatched += 1
                continue
            lat, lng = coords
            updates.append((store.store_id, lat, lng))
            if len(updates) >= _FLUSH_EVERY:
                geocoded += self._repository.update_coordinates(updates)
                updates = []
        if updates:
            geocoded += self._repository.update_coordinates(updates)
        return GeocodeResult(
            attempted=len(pending), geocoded=geocoded, unmatched=unmatched
        )
