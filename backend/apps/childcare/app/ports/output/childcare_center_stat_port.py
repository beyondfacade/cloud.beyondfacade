"""Driven Ports — 어린이집 현황 조회가 요구하는 계약."""

from abc import ABC, abstractmethod

from apps.childcare.domain.entities.childcare_center_stat_entity import ChildcareCenterStat


class ChildcareCenterStatRepositoryPort(ABC):
    @abstractmethod
    def list_latest(self, region_code: str) -> list[ChildcareCenterStat]:
        """행정동의 운영 중 시설별 최신 현황 (좌표 유무 무관)."""
