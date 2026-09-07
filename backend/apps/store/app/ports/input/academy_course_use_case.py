"""Driving Port — 학원 수집 UseCase 인터페이스."""

from abc import ABC, abstractmethod


class AcademyIngestUseCase(ABC):
    @abstractmethod
    def ingest(self) -> tuple[int, int]:
        """서울 학원·교습소 스냅샷 전량을 수집해 (점포 업서트 건수, 교습과정 재적재 건수)를 반환한다.

        원천이 현행 스냅샷만 제공(갱신시점 필터 없음)하므로 매 실행 전량 수집 — 업서트라 멱등.
        """
