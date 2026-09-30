from abc import ABC, abstractmethod
from datetime import datetime

from apps.ops.domain.entities.host_sample_entity import HostSample


class HostSampleRepositoryPort(ABC):
    @abstractmethod
    def add(self, sample: HostSample) -> None:
        """같은 시각 표본이 이미 있으면 덮어쓴다 (크론 중복 실행 대비)."""

    @abstractmethod
    def series(self, since: datetime, bucket_seconds: int) -> list[HostSample]:
        """since 이후 표본을 bucket_seconds 단위로 평균 — sampled_at은 버킷 시작 시각, 오래된 것부터."""

    @abstractmethod
    def delete_before(self, cutoff: datetime) -> int: ...
