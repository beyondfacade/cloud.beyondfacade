"""Driving Port — seoul_commerce_change_baseline 적재 UseCase 계약 (CLI가 유일한 Driving Adapter)."""

from abc import ABC, abstractmethod
from pathlib import Path

from apps.neighborhood.app.dtos.seoul_commerce_change_baseline_dto import (
    NeighborhoodIngestResultDto,
)


class SeoulCommerceChangeBaselineIngestUseCase(ABC):
    @abstractmethod
    def ingest(self, paths: list[Path]) -> NeighborhoodIngestResultDto:
        """원천 파일들을 멱등 적재한다. 재실행해도 행 수가 늘지 않는다."""
