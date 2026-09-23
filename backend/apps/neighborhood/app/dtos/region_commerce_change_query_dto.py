"""조회 경로 DTO — 적재 결과 DTO(region_commerce_change_dto)와 역할이 다르다 (ISP)."""

from dataclasses import dataclass


@dataclass
class SeoulBaselineDto:
    """같은 분기의 서울 전체 평균 — "110개월"은 "서울 117"이 옆에 있어야 읽힌다 (무대 설계서 §5-2)."""

    operating_months: float | None
    closed_months: float | None


@dataclass
class RegionCommerceChangeDto:
    region_code: str
    year_quarter: str
    change_code: str | None
    change_name: str | None
    operating_months: float | None
    closed_months: float | None
    seoul: SeoulBaselineDto | None = None  # baseline 행이 없는 분기면 None


@dataclass
class ChangeMetricValueDto:
    """단계구분도 응답 단위 — {region_code, value}. metric BC의 `/metrics`와 같은 계약이다."""

    region_code: str
    value: float
