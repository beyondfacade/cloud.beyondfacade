"""Driven Ports — 점포 적재가 요구하는 계약 (ISP: 원천 읽기 / 저장 분리)."""

from abc import ABC, abstractmethod
from pathlib import Path

from apps.commerce.domain.entities.region_commerce_store_entity import RegionCommerceStore


class RegionCommerceStoreGatewayPort(ABC):
    @abstractmethod
    def fetch_stores(self, path: Path) -> list[RegionCommerceStore]:
        """원천 파일 1개를 읽어 엔티티로 돌려준다. region_code는 아직 None."""


class RegionCommerceStoreRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, rows: list[RegionCommerceStore]) -> int:
        """PK(adstrd_code, service_industry_code, year_quarter) 기준 멱등 업서트. 처리 건수 반환."""
