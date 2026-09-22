"""학원·부동산 좌표 결측분 SGIS 지오코딩 인터랙터."""

from apps.store.app.ports.input.geocode_stores_use_case import (
    GeocodeResult,
    GeocodeStoresUseCase,
)
from apps.store.app.ports.output.geocoding_port import GeocodingGatewayPort
from apps.store.app.ports.output.store_geocode_port import StoreGeocodeRepositoryPort


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
        for store in pending:
            address = store.road_address or store.jibun_address
            if not address:
                unmatched += 1
                continue
            coords = self._gateway.geocode(address)
            if coords is None and store.jibun_address and store.road_address:
                # 도로명 실패 시 지번 폴백 (둘 다 있을 때만)
                coords = self._gateway.geocode(store.jibun_address)
            if coords is None:
                unmatched += 1
                continue
            lat, lng = coords
            updates.append((store.store_id, lat, lng))
        geocoded = self._repository.update_coordinates(updates)
        return GeocodeResult(
            attempted=len(pending), geocoded=geocoded, unmatched=unmatched
        )
