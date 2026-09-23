"""Driven Ports — finance가 바깥 세계에 요구하는 계약 (ISP: 원천별 분리)."""

from abc import ABC, abstractmethod

from apps.finance.app.dtos.finance_dto import RateBasis, RentBasis, RevenueBasis


class MasterLookupPort(ABC):
    @abstractmethod
    def district_of_region(self, region_code: str) -> str | None:
        """region → 소속 구 코드. 미등록이면 None."""

    @abstractmethod
    def industry_exists(self, industry_id: str) -> bool: ...


class RevenueFactsPort(ABC):
    @abstractmethod
    def latest_quarterly_sales_per_store(
        self, region_code: str, industry_id: str
    ) -> RevenueBasis | None:
        """업종에 매핑된 CS 코드 전부의 분기 매출 합·점포 합. 두 테이블 모두 있는 최신 분기. 없으면 None."""


class RentFactsPort(ABC):
    @abstractmethod
    def latest_zone_rent(self, zone_path: str) -> RentBasis | None:
        """R-ONE 권역(`region_level=2`)의 최신 분기 임대료. 없으면 None."""


class LoanRateFactsPort(ABC):
    @abstractmethod
    def latest_facility_rate(self) -> RateBasis | None:
        """ECOS 시설자금대출(`loan_facility`) 최신. 없으면 None."""
