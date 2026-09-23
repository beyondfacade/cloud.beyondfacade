from dataclasses import dataclass, field


@dataclass(frozen=True)
class LlmSuggestion:
    """LLM 폴백이 준 제안 — 마스터로 검증하기 전의 값. 검증 통과분만 초안에 들어간다."""

    region_name: str | None = None
    industry_id: str | None = None
    budget_krw: int | None = None


@dataclass
class RegionCandidateDto:
    region_code: str
    region_name: str
    district_code: str
    district_name: str


@dataclass
class DiagnosisDto:
    type_code: str
    type_name: str
    time_label: str | None
    peak_sales_band: str | None
    sentence: str
    year_quarter: str
    hour_gap_quarter: str | None


@dataclass
class IntentResultDto:
    intent_type: str  # A | B | C
    region_code: str | None
    region_name: str | None
    district_code: str | None
    industry_id: str | None
    budget_krw: int | None
    missing: list[str]
    candidates: list[RegionCandidateDto] = field(default_factory=list)
    diagnosis: DiagnosisDto | None = None
    source: str = "rule"  # rule | llm
