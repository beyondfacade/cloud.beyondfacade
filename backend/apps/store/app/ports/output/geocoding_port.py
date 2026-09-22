"""Driven Port — SGIS 주소 지오코딩 게이트웨이 계약."""

from abc import ABC, abstractmethod


class GeocodingGatewayPort(ABC):
    @abstractmethod
    def geocode(self, address: str) -> tuple[float, float] | None:
        """주소 → (lat, lng) WGS84. 매칭 실패·무결과는 None."""
