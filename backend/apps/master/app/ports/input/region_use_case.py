"""Driving Port — region UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.master.app.dtos.region_dto import RegionDto, RegionSummaryDto


class RegionUseCase(ABC):
    @abstractmethod
    def myself(self) -> RegionDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def geojson(self) -> dict:
        """서울 행정동 경계 FeatureCollection — properties={region_code, name}."""

    @abstractmethod
    def summary(self, region_code: str, industry_id: str) -> RegionSummaryDto:
        """사이드패널 카드 — 최신 연도 지표 fact 3장 (점포수·폐업률·성장률).

        미등록 행정동코드는 RegionNotFoundError, 집계 없으면 value="데이터 없음".
        """
