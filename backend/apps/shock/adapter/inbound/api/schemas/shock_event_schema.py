from datetime import date

from pydantic import BaseModel


class IndustryImpactResponse(BaseModel):
    industry_id: str
    severity: str


class ShockEventResponse(BaseModel):
    event_id: str
    layer: str
    name: str
    start_date: date
    scope: str
    source: str
    end_date: date | None = None
    source_url: str | None = None
    description: str | None = None
    industry_impacts: list[IndustryImpactResponse] = []
