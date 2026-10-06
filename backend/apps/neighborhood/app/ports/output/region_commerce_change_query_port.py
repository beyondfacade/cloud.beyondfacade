"""Driven Port — region_commerce_change 조회가 요구하는 계약 (적재 포트와 역할 분리, ISP)."""

from abc import ABC, abstractmethod

from apps.neighborhood.domain.entities.region_commerce_change_entity import (
    RegionCommerceChange,
)


class RegionCommerceChangeQueryPort(ABC):
    @abstractmethod
    def find(self, region_code: str, year_quarter: str) -> RegionCommerceChange | None:
        """동×분기 단건 — 없으면 None."""

    @abstractmethod
    def find_latest(self, region_code: str) -> RegionCommerceChange | None:
        """그 동의 가장 최근 분기 행 — 없으면 None. 화면은 최신이 언제인지 모른다."""
