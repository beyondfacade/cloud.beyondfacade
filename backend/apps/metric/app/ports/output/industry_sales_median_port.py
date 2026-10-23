"""Driven Port — 업종×분기 서울 점포당 매출 중앙값 저장소."""

from abc import ABC, abstractmethod


class IndustrySalesMedianRepositoryPort(ABC):
    @abstractmethod
    def rebuild(self) -> int:
        """상권 원천 전 분기로 업종×분기 중앙값을 통째로 다시 만들고 행 수를 반환한다 (멱등)."""
