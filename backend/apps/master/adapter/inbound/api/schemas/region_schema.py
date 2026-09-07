from pydantic import BaseModel


class RegionResponse(BaseModel):
    region_code: str
    name: str


class SummaryCardResponse(BaseModel):
    label: str
    value: str
    grade: str  # fact / signal — 프론트엔드 신뢰 배지 계약


class RegionSummaryResponse(BaseModel):
    region_code: str
    name: str
    industry_id: str
    cards: list[SummaryCardResponse]
