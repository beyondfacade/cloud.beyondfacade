"""Driven Ports — 설비실이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from datetime import datetime

from apps.ops.app.dtos.facility_dto import DatabaseStatusDto, GpuDto, HostMetricsDto


class HostMetricsPort(ABC):
    @abstractmethod
    def read(self) -> HostMetricsDto: ...


class GpuMetricsPort(ABC):
    @abstractmethod
    def read(self) -> list[GpuDto]:
        """GPU가 없거나 조회 도구가 없으면 빈 목록."""


class DatabaseStatusPort(ABC):
    @abstractmethod
    def read(self) -> DatabaseStatusDto: ...

    @abstractmethod
    def table_stats(self, table: str, time_column: str | None) -> tuple[int | None, datetime | None]:
        """(추정 행 수, time_column 최댓값). 테이블이 없으면 (None, None)."""


class CollectorLogPort(ABC):
    @abstractmethod
    def last_modified(self, log_file: str) -> datetime | None: ...

    @abstractmethod
    def tail(self, log_file: str, lines: int) -> list[str]:
        """마지막 lines줄 (원문 그대로 — 가림은 유스케이스가 한다). 파일이 없으면 빈 목록."""


class CollectorRunnerPort(ABC):
    @abstractmethod
    def is_running(self, key: str) -> bool: ...

    @abstractmethod
    def start(self, key: str) -> None:
        """scripts/<key>.sh를 분리된 프로세스로 띄우고 곧바로 돌아온다."""
