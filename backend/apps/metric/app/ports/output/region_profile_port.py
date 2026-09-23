"""Driven Ports — region_profile이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.metric.app.dtos.region_profile_dto import RegionQuarterObservation
from apps.metric.domain.entities.region_profile_entity import RegionProfile


class RegionProfileRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, profiles: list[RegionProfile]) -> int:
        """(region_code, year_quarter) 기준 업서트 — 처리 건수 반환."""

    @abstractmethod
    def find(self, region_code: str, year_quarter: str) -> RegionProfile | None:
        """복합키 단건 조회 — 없으면 None."""

    @abstractmethod
    def find_latest(self, region_code: str) -> RegionProfile | None:
        """그 동의 year_quarter 최대 행 — 없으면 None."""


class NeighborhoodObservationPort(ABC):
    @abstractmethod
    def quarter_observations(self, quarters: list[str]) -> list[RegionQuarterObservation]:
        """해당 분기들의 행정동별 동네 맥락 원자료 (region_code 보유분만)."""
