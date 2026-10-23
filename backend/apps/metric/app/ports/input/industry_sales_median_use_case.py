"""Driving Port — industry_sales_median_quarter UseCase 인터페이스."""

from abc import ABC, abstractmethod


class IndustrySalesMedianUseCase(ABC):
    @abstractmethod
    def build(self) -> int:
        """업종×분기 서울 점포당 매출 중앙값을 다시 계산해 저장하고 행 수를 반환한다 (멱등)."""
