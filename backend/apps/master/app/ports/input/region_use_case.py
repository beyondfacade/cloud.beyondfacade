"""Driving Port — region UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.master.app.dtos.region_dto import RegionDto


class RegionUseCase(ABC):
    @abstractmethod
    def myself(self) -> RegionDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def geojson(self) -> dict:
        """서울 행정동 경계 FeatureCollection — properties={region_code, name}."""
