"""Driven Ports — 편의점 스냅샷 수집·조회가 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import date

from apps.convenience.domain.entities.convenience_store_entity import ConvenienceStore


class ConvenienceGatewayPort(ABC):
    @abstractmethod
    def iter_stores(self, region_code: str) -> Iterator[ConvenienceStore]:
        """해당 행정동의 편의점 현행 스냅샷을 페이징 순회하며 엔티티로 반환한다."""


class ConvenienceSnapshotRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, stores: list[ConvenienceStore], observed_on: date) -> int:
        """store_id 기준 멱등 업서트 — 신규는 first/last_seen=관측일, 기존은
        last_seen만 전진(first_seen 보존). 처리 건수 반환."""


class ConvenienceStoreQueryRepositoryPort(ABC):
    @abstractmethod
    def list_current(self, region_code: str) -> list[ConvenienceStore]:
        """행정동의 현행 편의점 — 행정동 최신 관측일(max last_seen_on)에 관측된 점포 (좌표 유무 무관)."""


class RegionCatalogPort(ABC):
    @abstractmethod
    def exists(self, region_code: str) -> bool:
        """region 마스터 등록 여부."""
