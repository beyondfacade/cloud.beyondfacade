"""Proxy (GoF) — geojson 캐시. 경계는 반기 갱신 데이터라 프로세스 수명 캐시로 충분."""

from apps.master.app.dtos.region_dto import RegionDto, RegionSummaryDto
from apps.master.app.ports.input.region_use_case import RegionUseCase


class CachingRegionUseCaseProxy(RegionUseCase):
    def __init__(self, inner: RegionUseCase) -> None:
        self._inner = inner
        self._geojson: dict | None = None

    def myself(self) -> RegionDto:
        return self._inner.myself()

    def geojson(self) -> dict:
        if self._geojson is None:
            self._geojson = self._inner.geojson()
        return self._geojson

    def summary(self, region_code: str, industry_id: str) -> RegionSummaryDto:
        return self._inner.summary(region_code, industry_id)  # 지표는 일 배치 갱신 — 캐시 없음
