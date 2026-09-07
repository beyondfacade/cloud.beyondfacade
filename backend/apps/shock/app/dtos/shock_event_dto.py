from dataclasses import dataclass, field
from datetime import date


@dataclass
class IndustryImpactDto:
    industry_id: str
    severity: str


@dataclass
class ShockEventDto:
    event_id: str
    layer: str
    name: str
    start_date: date
    scope: str
    source: str
    end_date: date | None = None
    source_url: str | None = None
    description: str | None = None
    industry_impacts: list[IndustryImpactDto] = field(default_factory=list)
