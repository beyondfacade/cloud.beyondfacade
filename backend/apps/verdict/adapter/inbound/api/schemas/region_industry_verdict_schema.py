from datetime import datetime

from pydantic import BaseModel


class SignalResultResponse(BaseModel):
    key: str
    level: str
    value: float | None
    percentile: float | None
    evidence: str
    source: str
    band: str | None = None
    band_label: str | None = None


class RegionIndustryVerdictResponse(BaseModel):
    region_code: str
    industry_id: str
    verdict_code: str
    strong_count: int
    on_count: int
    signals: list[SignalResultResponse]
    computed_at: datetime
    basis: str  # permit | proxy | aggregate — 카드 배지 (업종 특화 신호 설계서 §9-3)


class VerdictValueResponse(BaseModel):
    """단계구분도 응답 단위 — {region_code, value: verdict_code}. 동네 유형과 같은 범주 계약 (프론트엔드 계약)."""

    region_code: str
    value: str


class AlternativeIndustryResponse(BaseModel):
    industry_id: str
    industry_name: str
    verdict_code: str
    strong_count: int
    on_count: int


class AlternativeRegionResponse(BaseModel):
    region_code: str
    region_name: str
    verdict_code: str
    strong_count: int
    on_count: int


class VerdictAlternativesResponse(BaseModel):
    """대안 두 축 (설계서 §12) — industries 동네 고정 · regions 업종 고정(같은 neighborhood_type 안에서)."""

    region_code: str
    industry_id: str
    neighborhood_type: str | None
    industries: list[AlternativeIndustryResponse]
    regions: list[AlternativeRegionResponse]
