"""Driving Ports — 어린이집 스냅샷 수집·조회 UseCase 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from datetime import date

from apps.childcare.app.dtos.childcare_center_dto import ChildcareCenterDto


class ChildcareSnapshotUseCase(ABC):
    @abstractmethod
    def ingest(self, district_code: str, observed_on: date) -> int:
        """자치구 스냅샷 전량 업서트(시설 + 기준일 현황) — 처리 건수 반환.
        소실 시설은 last_seen_on 정지로 남는다(폐원 판정 없음 — 후속 분석 몫)."""


class ChildcareCenterQueryUseCase(ABC):
    @abstractmethod
    def myself(self) -> ChildcareCenterDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def list_centers(self, region_code: str) -> list[ChildcareCenterDto]:
        """지도 마커용 — 행정동의 운영 중·좌표 보유 시설과 최신 현황. 미등록 행정동은 RegionNotFoundError."""
