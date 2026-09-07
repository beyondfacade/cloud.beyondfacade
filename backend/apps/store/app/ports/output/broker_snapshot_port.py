"""Driven Ports — 부동산중개업(molit_broker) 스냅샷 수집이 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import date

from apps.store.domain.entities.store_entity import Store


class BrokerGatewayPort(ABC):
    @abstractmethod
    def iter_offices(self, industry_id: str, district_code: str) -> Iterator[Store]:
        """해당 자치구의 중개사무소 현행 스냅샷을 페이징 순회하며 엔티티로 반환한다."""


class StoreSnapshotRepositoryPort(ABC):
    """스냅샷 전량 재수집 흐름(업서트 + 소실 폐업 추정 + 위치 이월)이 요구하는 저장소 역할."""

    @abstractmethod
    def upsert(self, stores: list[Store]) -> int:
        """store_id 기준 업서트 — 처리 건수 반환."""

    @abstractmethod
    def active_store_ids(self, industry_id: str, district_code: str) -> set[str]:
        """close_date 없는(영업 관측 중) 점포 ID 집합 — 폐업 추정 비교 기준."""

    @abstractmethod
    def existing_locations(
        self, industry_id: str, district_code: str
    ) -> dict[str, tuple[float, float, str | None]]:
        """좌표 보유 점포의 (lat, lng, region_code) — 원천에 좌표가 없어
        재수집 업서트가 후속 지오코딩·공간조인 결과를 지우지 않도록 이월한다."""

    @abstractmethod
    def mark_closed(
        self, store_ids: list[str], close_date: date, status_code: str, status_name: str
    ) -> int:
        """스냅샷에서 사라진 점포를 폐업(추정) 처리 — 갱신 건수 반환."""
