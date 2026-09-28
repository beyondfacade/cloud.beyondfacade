from datetime import datetime

from pydantic import BaseModel


class SignalResultResponse(BaseModel):
    key: str
    level: str
    value: float | None
    percentile: float | None
    evidence: str
    source: str


class RegionIndustryVerdictResponse(BaseModel):
    region_code: str
    industry_id: str
    verdict_code: str
    strong_count: int
    on_count: int
    signals: list[SignalResultResponse]
    computed_at: datetime


class VerdictValueResponse(BaseModel):
    """단계구분도 응답 단위 — {region_code, value: verdict_code}. 동네 유형과 같은 범주 계약 (프론트엔드 계약)."""

    region_code: str
    value: str
