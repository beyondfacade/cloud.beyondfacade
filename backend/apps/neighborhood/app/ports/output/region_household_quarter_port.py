"""Driven Ports — region_household_quarter 적재가 요구하는 계약 (ISP: 원천 읽기 / 저장 분리).

게이트웨이가 list가 아니라 Iterator를 돌려주는 근거: 원본 1행이 여러 행으로 펼쳐져 긴 형태
전체가 약 106만 행이다. 인터랙터가 청크 단위로 받아 업서트하고 버린다 (commerce 분해 전례).
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path

from apps.neighborhood.domain.entities.region_household_quarter_entity import (
    RegionHouseholdQuarter,
)


class RegionHouseholdQuarterGatewayPort(ABC):
    @abstractmethod
    def fetch_households(self, path: Path) -> Iterator[RegionHouseholdQuarter]:
        """원천 CSV 1개를 읽어 엔티티를 흘려보낸다. region_code는 아직 None."""


class RegionHouseholdQuarterRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, rows: list[RegionHouseholdQuarter]) -> int:
        """PK(adstrd_code, year_quarter, dim_type, dim_key) 기준 멱등 업서트. 처리 건수 반환."""
