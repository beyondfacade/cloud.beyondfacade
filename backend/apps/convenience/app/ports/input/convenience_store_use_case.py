"""Driving Port — 편의점 스냅샷 수집 UseCase 계약."""

from abc import ABC, abstractmethod
from datetime import date


class ConvenienceSnapshotUseCase(ABC):
    @abstractmethod
    def ingest(self, region_code: str, observed_on: date) -> int:
        """행정동 스냅샷 전량 업서트 — 처리 건수 반환. 소실분은 last_seen_on 정지로
        남는다(폐점 판정 없음 — 원천이 개폐업 분석 불가, api.md §2-3)."""
