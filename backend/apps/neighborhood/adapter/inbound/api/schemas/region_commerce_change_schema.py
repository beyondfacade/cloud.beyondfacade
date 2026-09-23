from pydantic import BaseModel


class SeoulBaselineResponse(BaseModel):
    """같은 분기의 서울 전체 평균 — 동의 값 옆에 놓는 비교 기준."""

    operating_months: float | None
    closed_months: float | None


class RegionCommerceChangeResponse(BaseModel):
    region_code: str
    year_quarter: str
    change_code: str | None  # HH | HL | LH | LL
    change_name: str | None  # 정체 | 상권축소 | 상권확장 | 다이나믹
    operating_months: float | None  # 운영 영업 개월 평균
    closed_months: float | None  # 폐업 영업 개월 평균
    seoul: SeoulBaselineResponse | None = None  # baseline 행이 없는 분기면 null


class ChangeMetricValueResponse(BaseModel):
    """단계구분도 응답 단위 — metric BC의 `/metrics`와 같은 {region_code, value} 계약."""

    region_code: str
    value: float
