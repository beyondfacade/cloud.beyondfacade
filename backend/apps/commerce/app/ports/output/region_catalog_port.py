"""Driven Port — region 마스터 조회 (매출·점포 두 프랙탈이 횡단 공유하는 공통 포트).

행마다 DB를 조회하지 않기 위해 8자리 키 맵을 한 번에 받는 계약으로 둔다.
"""

from abc import ABC, abstractmethod


class RegionCatalogPort(ABC):
    @abstractmethod
    def region_code_by_adstrd(self) -> dict[str, str]:
        """region_code 앞 8자리 → region_code 10자리 맵 (서울 427행 1회 로드)."""
