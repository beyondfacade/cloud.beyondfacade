"""Driving Port — 관리자 기록 보존 정리 (매일 크론)."""

from abc import ABC, abstractmethod

from apps.admin.app.dtos.housekeeping_dto import HousekeepingResultDto


class HousekeepingUseCase(ABC):
    @abstractmethod
    def run(self) -> HousekeepingResultDto:
        """보존 기간이 지난 이벤트·감사 로그와 만료된 세션·IP 차단을 지우고 지운 건수를 돌려준다."""
