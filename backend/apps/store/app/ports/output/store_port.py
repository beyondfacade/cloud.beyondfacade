"""Driven Ports — store가 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime

from apps.store.app.dtos.store_dto import IngestTarget
from apps.store.domain.entities.store_entity import Store


class StoreRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, stores: list[Store]) -> int:
        """store_id 기준 업서트 (신규 삽입, 기존 갱신) — 처리 건수 반환."""

    @abstractmethod
    def latest_source_updated_at(
        self, industry_id: str, district_code: str
    ) -> datetime | None:
        """증분 수집 커서 — 해당 업종×자치구의 최근 원천 갱신시점."""


class StorePermitGatewayPort(ABC):
    @abstractmethod
    def iter_stores(
        self, target: IngestTarget, updated_since: datetime | None
    ) -> Iterator[Store]:
        """대상의 인허가 데이터를 페이징 순회하며 엔티티로 반환한다."""
