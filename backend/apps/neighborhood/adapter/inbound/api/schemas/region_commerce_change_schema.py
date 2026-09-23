from pydantic import BaseModel


class RegionCommerceChangeResponse(BaseModel):
    region_code: str
    year_quarter: str
    change_code: str | None  # HH | HL | LH | LL
    change_name: str | None  # 정체 | 상권축소 | 상권확장 | 다이나믹
    operating_months: float | None  # 운영 영업 개월 평균
    closed_months: float | None  # 폐업 영업 개월 평균


class ChangeMetricValueResponse(BaseModel):
    """단계구분도 응답 단위 — metric BC의 `/metrics`와 같은 {region_code, value} 계약."""

    region_code: str
    value: float
