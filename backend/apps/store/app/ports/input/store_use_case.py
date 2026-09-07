"""Driving Port — store UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.store.app.dtos.store_dto import IngestTarget, StoreDto


class StoreUseCase(ABC):
    @abstractmethod
    def myself(self) -> StoreDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def ingest(self, targets: list[IngestTarget], *, full: bool = False) -> int:
        """대상(업종×자치구)별 인허가 데이터를 증분 수집·업서트하고 처리 건수를 반환한다.

        full=True면 증분 커서를 무시하고 전체를 다시 받는다 (부분 적재 복구용 — 업서트라 멱등).
        """

    @abstractmethod
    def list_open_stores(self, region_code: str, industry_id: str) -> list[StoreDto]:
        """지도 마커용 — 해당 행정동×업종의 영업 중 점포 목록 (좌표 없는 행 제외).

        미등록 업종은 IndustryNotFoundError.
        """
