"""조회 경로 DTO — 적재 결과 DTO(region_commerce_change_dto)와 역할이 다르다 (ISP)."""

from dataclasses import dataclass


@dataclass
class RegionCommerceChangeDto:
    region_code: str
    year_quarter: str
    change_code: str | None
    change_name: str | None
    operating_months: float | None
    closed_months: float | None


@dataclass
class ChangeMetricValueDto:
    """단계구분도 응답 단위 — {region_code, value}. metric BC의 `/metrics`와 같은 계약이다."""

    region_code: str
    value: float
