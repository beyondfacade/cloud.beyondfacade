"""Driven Ports — store가 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from datetime import date, datetime

from apps.store.app.dtos.store_dto import IngestTarget
from apps.store.domain.entities.store_entity import Store


class StoreRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, stores: list[Store]) -> int:
        """store_id 기준 업서트 (신규 삽입, 기존 갱신) — 처리 건수 반환."""

    @abstractmethod
    def latest_source_updated_at(
        self, industry_ids: Sequence[str], district_code: str
    ) -> datetime | None:
        """증분 수집 커서 — 해당 업종들×자치구의 최근 원천 갱신시점.

        한 슬러그가 여러 업종을 담으면(일반음식점) 그 업종 집합 전체의 max 가 커서다.
        """

    @abstractmethod
    def list_open(self, region_code: str, industry_id: str) -> list[Store]:
        """해당 행정동×업종의 영업 중(close_date 없음)·좌표 보유 점포 목록."""

    @abstractmethod
    def list_closed_since(self, region_code: str, industry_id: str, since: date) -> list[Store]:
        """해당 행정동×업종의 폐업 점포(close_date ≥ since)·좌표 보유 목록 — 폐업 마커용."""


class IndustryCatalogPort(ABC):
    @abstractmethod
    def exists(self, industry_id: str) -> bool:
        """industry 마스터 등록 여부."""


class StorePermitGatewayPort(ABC):
    @abstractmethod
    def iter_stores(
        self, target: IngestTarget, updated_since: datetime | None
    ) -> Iterator[Store]:
        """대상의 인허가 데이터를 페이징 순회하며 엔티티로 반환한다."""
