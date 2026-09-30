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


@dataclass
class FundingCandidateDto:
    """후보 공고 1건 — 공고 + 어느 규칙에 걸렸는지(`why`)."""

    program: FundingProgramDto
    why: str


@dataclass
class FundingCandidateListDto:
    """후보 목록 + 화면이 문장을 쓰기 위해 되돌려받는 요청 값.

    `industry_id`·`external_funding_need`는 **필터에 쓰이지 않는다** — 공고에 업종·한도가 구조화돼
    있지 않다. 화면이 "조달 필요 3,160만 원 기준 후보"라고만 쓰도록 그대로 돌려준다 (설계서 §3).
    """

    candidates: list[FundingCandidateDto]
    industry_id: str | None = None
    external_funding_need: int | None = None
    stage: str | None = None


@dataclass
class RateDto:
    """금리 최신값 1건 — `rate_type`은 ECOS 계열(base 기준금리 · loan_facility 시설자금대출)."""

    rate_type: str
    period: str  # YYYYMM
    rate_pct: float


@dataclass
class SupportItemDto:
    program: FundingProgramDto
    why: str
    district_match: bool
    industry_match: bool


@dataclass
class SupportGuideDto:
    """창업 지원 정보 — 대출·보증 / 우리 구 전용 / 창업·경영 세 묶음 + 금리 참고값."""

    region_code: str | None
    district_name: str | None
    industry_id: str | None
    loans: list[SupportItemDto]
    district: list[SupportItemDto]
    others: list[SupportItemDto]
    rates: list[RateDto]
