"""Driven Ports — 어린이집 스냅샷 수집·조회가 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from datetime import date

from apps.childcare.domain.entities.childcare_center_entity import ChildcareCenter


class ChildcareGatewayPort(ABC):
    @abstractmethod
    def fetch_centers(self, district_code: str) -> list[ChildcareCenter]:
        """해당 자치구의 폐지 제외 어린이집 전량 — 1회 호출에 구 전체가 온다(페이징 없음 실측)."""


class ChildcareSnapshotRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, centers: list[ChildcareCenter], observed_on: date) -> int:
        """center_id 기준 시설 멱등 업서트(first_seen·region_code 보존, last_seen 전진)
        + (center_id, base_date) 현황 업서트. 처리 건수 반환."""


class ChildcareCenterQueryRepositoryPort(ABC):
    @abstractmethod
    def list_operating(self, region_code: str) -> list[ChildcareCenter]:
        """행정동의 운영 중(자치구 최신 관측일에 관측)·좌표 보유 시설 — stat은 시설별 최신 기준일."""


class RegionCatalogPort(ABC):
    @abstractmethod
    def exists(self, region_code: str) -> bool:
        """region 마스터 등록 여부."""
