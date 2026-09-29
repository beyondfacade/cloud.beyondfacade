"""analysis API 요청/응답 스키마."""

from pydantic import BaseModel, Field


class AnalysisCreateRequest(BaseModel):
    region: str
    industry: str
    question: str | None = None
    model: str = Field(default="hybrid", pattern="^(hybrid|gemma3|gemini)$")
    budget: int | None = None  # 관문에서 넘어온 예산(원) — finance 도구 기본값이 된다


class AnalysisCreateResponse(BaseModel):
    analysis_id: str


class AnalysisMyselfResponse(BaseModel):
    analysis_id: str
    region_code: str
    industry: str
    model: str
