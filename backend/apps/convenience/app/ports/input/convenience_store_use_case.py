"""Driving Ports — 편의점 스냅샷 수집·조회 UseCase 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from datetime import date

from apps.convenience.app.dtos.convenience_store_dto import (
    ConvenienceRegionSummaryDto,
    ConvenienceStoreDto,
)


class ConvenienceSnapshotUseCase(ABC):
    @abstractmethod
    def ingest(self, region_code: str, observed_on: date) -> int:
        """행정동 스냅샷 전량 업서트 — 처리 건수 반환. 소실분은 last_seen_on 정지로
        남는다(폐점 판정 없음 — 원천이 개폐업 분석 불가, api.md §2-3)."""


class ConvenienceStoreQueryUseCase(ABC):
    @abstractmethod
    def myself(self) -> ConvenienceStoreDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def list_stores(self, region_code: str) -> list[ConvenienceStoreDto]:
        """지도 마커용 — 행정동의 현행·좌표 보유 편의점. 미등록 행정동은 RegionNotFoundError."""

    @abstractmethod
    def summarize_region(self, region_code: str) -> ConvenienceRegionSummaryDto:
        """행정동 현행 편의점 수·브랜드 분포. 미등록 행정동은 RegionNotFoundError."""
