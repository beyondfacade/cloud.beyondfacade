"""Driven Ports — region이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.master.domain.entities.region_entity import Region


class RegionRepositoryPort(ABC):
    @abstractmethod
    def list_regions(self) -> list[Region]:
        """전체 행정동을 region_code 순으로 반환한다."""


class RegionBoundaryReaderPort(ABC):
    @abstractmethod
    def read_feature(self, geometry_ref: str) -> dict:
        """geometry_ref 경로의 경계 GeoJSON Feature를 읽어 반환한다."""
