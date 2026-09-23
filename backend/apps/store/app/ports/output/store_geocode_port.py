"""Driven Port — 지오코딩 대기열 저장소 계약."""

from abc import ABC, abstractmethod

from apps.store.domain.entities.store_entity import Store


class StoreGeocodeRepositoryPort(ABC):
    @abstractmethod
    def list_pending(
        self, industry_ids: list[str], limit: int | None = None
    ) -> list[Store]:
        """lat NULL 이고 주소가 있는 점포 — 지오코딩 대기열."""

    @abstractmethod
    def update_coordinates(
        self, updates: list[tuple[str, float, float]]
    ) -> int:
        """(store_id, lat, lng) 일괄 기입 — 갱신 건수."""
