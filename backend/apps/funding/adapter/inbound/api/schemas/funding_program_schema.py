from datetime import date

from pydantic import BaseModel


class FundingProgramResponse(BaseModel):
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


class FundingCandidateResponse(FundingProgramResponse):
    """후보 공고 — 공고 필드 + 걸린 규칙 한 줄."""

    why: str


class FundingCandidateListResponse(BaseModel):
    """후보 목록 + 요청 값 되돌림.

    `industry_id`·`external_funding_need`는 필터에 쓰이지 않는다 — 화면이 문장에 쓰라고 돌려줄 뿐이다.
    """

    candidates: list[FundingCandidateResponse]
    industry_id: str | None = None
    external_funding_need: int | None = None
    stage: str | None = None


class SupportItemResponse(FundingCandidateResponse):
    district_match: bool
    industry_match: bool


class RateResponse(BaseModel):
    rate_type: str
    period: str
    rate_pct: float


class SupportGuideResponse(BaseModel):
    """창업 지원 정보 — 대출·보증 / 우리 구 전용 / 창업·경영 + 금리 참고값. 자격 확정이 아니다."""

    region_code: str | None = None
    district_name: str | None = None
    industry_id: str | None = None
    loans: list[SupportItemResponse]
    district: list[SupportItemResponse]
    others: list[SupportItemResponse]
    rates: list[RateResponse]
