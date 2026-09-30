"""Driving Port — 설비 지표 표본 적재(크론)와 추세 조회."""

from abc import ABC, abstractmethod

from apps.ops.app.dtos.ops_history_dto import HostHistoryDto, HostPointDto


class HostHistoryUseCase(ABC):
    @abstractmethod
    def myself(self) -> HostHistoryDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def sample(self) -> tuple[HostPointDto, int]:
        """지금 지표를 한 표본으로 저장하고 보존 기간이 지난 표본을 지운다 — (표본, 지운 수)."""

    @abstractmethod
    def history(self, hours: int) -> HostHistoryDto: ...
