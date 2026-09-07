"""Driving Port — 부동산중개업 스냅샷 수집 UseCase 계약."""

from abc import ABC, abstractmethod
from datetime import date


class BrokerSnapshotUseCase(ABC):
    @abstractmethod
    def ingest(
        self, industry_id: str, district_code: str, observed_on: date
    ) -> tuple[int, int]:
        """자치구 스냅샷 전량 업서트 + 소실분 폐업(추정) — (업서트, 폐업추정) 건수 반환."""
