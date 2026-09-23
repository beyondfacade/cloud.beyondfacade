from pydantic import BaseModel


class IntentRequest(BaseModel):
    """두 형태 — 문장(`text`) 또는 되묻기로 완성된 코드 쌍(`region_code`+`industry_id`)."""

    text: str | None = None
    region_code: str | None = None
    industry_id: str | None = None


class RegionCandidateResponse(BaseModel):
    region_code: str
    region_name: str
    district_code: str
    district_name: str


class DiagnosisResponse(BaseModel):
    type_code: str
    type_name: str
    time_label: str | None
    peak_sales_band: str | None  # 매출 강도 최대 구간 — gap이 아니다
    sentence: str
    year_quarter: str
    hour_gap_quarter: str | None


class IntentResponse(BaseModel):
    intent_type: str  # A 동+업종 · B 동만 · C 동 없음
    region_code: str | None
    region_name: str | None
    district_code: str | None
    industry_id: str | None
    budget_krw: int | None
    missing: list[str]
    candidates: list[RegionCandidateResponse]
    diagnosis: DiagnosisResponse | None
    source: str  # rule | llm
