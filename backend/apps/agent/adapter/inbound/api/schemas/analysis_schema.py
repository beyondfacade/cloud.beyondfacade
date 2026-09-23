"""analysis API 요청/응답 스키마."""

from pydantic import BaseModel, Field


class AnalysisCreateRequest(BaseModel):
    region: str
    industry: str
    question: str | None = None
    model: str = Field(default="gemma3", pattern="^(gemma3|gemini)$")


class AnalysisCreateResponse(BaseModel):
    analysis_id: str


class AnalysisMyselfResponse(BaseModel):
    analysis_id: str
    region_code: str
    industry: str
    model: str
