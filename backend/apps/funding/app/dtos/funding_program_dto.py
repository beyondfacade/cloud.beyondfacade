from dataclasses import dataclass
from datetime import date


@dataclass
class FundingProgramDto:
    program_id: str
    source: str
    title: str
    org: str
    url: str
    apply_period: str
    exec_org: str | None = None
    field_category: str | None = None
    field_subcategory: str | None = None
    target_text: str | None = None
    hashtags: str | None = None
    apply_begin: date | None = None
    deadline: date | None = None
    summary: str | None = None
    is_expired: bool = False
