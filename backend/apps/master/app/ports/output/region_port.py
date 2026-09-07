"""Driven Ports — region이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.master.app.dtos.region_dto import RegionMetricSnapshot
from apps.master.domain.entities.region_entity import Region


class RegionRepositoryPort(ABC):
    @abstractmethod
    def list_regions(self) -> list[Region]:
        """전체 행정동을 region_code 순으로 반환한다."""

    @abstractmethod
    def find(self, region_code: str) -> Region | None:
        """행정동코드 단건 조회 — 없으면 None."""


class RegionBoundaryReaderPort(ABC):
    @abstractmethod
    def read_feature(self, geometry_ref: str) -> dict:
        """geometry_ref 경로의 경계 GeoJSON Feature를 읽어 반환한다."""


class RegionMetricSummaryPort(ABC):
    @abstractmethod
    def fetch(self, region_code: str, industry_id: str) -> RegionMetricSnapshot | None:
        """해당 행정동×업종의 최신 연도 지표 스냅샷 — 집계 데이터 없으면 None."""
