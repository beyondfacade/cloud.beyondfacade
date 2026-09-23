"""Driving Port — 학원·부동산 등 좌표 결측분 SGIS 지오코딩 UseCase."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GeocodeResult:
    attempted: int
    geocoded: int
    unmatched: int


class GeocodeStoresUseCase(ABC):
    @abstractmethod
    def run(
        self, industry_ids: list[str], limit: int | None = None
    ) -> GeocodeResult:
        """대기열을 지오코딩해 lat/lng를 채운다."""
