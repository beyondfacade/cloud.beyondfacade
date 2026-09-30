"""Driving Port — 설비실 (호스트·GPU·DB·수집기 상태)."""

from abc import ABC, abstractmethod

from apps.ops.app.dtos.facility_dto import FacilitySnapshotDto, ServiceCheckDto


class FacilityUseCase(ABC):
    @abstractmethod
    def myself(self) -> ServiceCheckDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def snapshot(self) -> FacilitySnapshotDto: ...
