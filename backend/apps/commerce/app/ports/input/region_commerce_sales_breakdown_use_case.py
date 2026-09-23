"""Driving Port — 추정매출 분해 적재 UseCase 계약 (CLI가 유일한 Driving Adapter)."""

from abc import ABC, abstractmethod
from pathlib import Path

from apps.commerce.app.dtos.region_commerce_sales_breakdown_dto import CommerceIngestResultDto


class RegionCommerceSalesBreakdownIngestUseCase(ABC):
    @abstractmethod
    def ingest(self, paths: list[Path]) -> CommerceIngestResultDto:
        """원천 파일들을 멱등 적재한다. 재실행해도 행 수가 늘지 않는다."""
