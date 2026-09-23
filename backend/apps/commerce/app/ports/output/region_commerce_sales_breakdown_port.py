"""Driven Ports — 분해 적재가 요구하는 계약 (ISP: 원천 읽기 / 저장 분리).

게이트웨이가 list가 아니라 Iterator를 돌려주는 근거: 원본 1행이 23행으로 펼쳐져 파일 1개가
약 158만 행이다(전체 789만). list로 들고 있으면 한 파일치가 수백 MB가 된다 — 매출·점포
프랙탈과 달리 스트리밍 계약으로 둔다.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path

from apps.commerce.domain.entities.region_commerce_sales_breakdown_entity import (
    RegionCommerceSalesBreakdown,
)


class RegionCommerceSalesBreakdownGatewayPort(ABC):
    @abstractmethod
    def fetch_breakdown(self, path: Path) -> Iterator[RegionCommerceSalesBreakdown]:
        """원천 파일 1개를 읽어 구간 엔티티를 흘려보낸다. region_code는 아직 None."""


class RegionCommerceSalesBreakdownRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, rows: list[RegionCommerceSalesBreakdown]) -> int:
        """PK(adstrd_code, 업종, 년분기, dim_type, dim_key) 기준 멱등 업서트. 처리 건수 반환."""
