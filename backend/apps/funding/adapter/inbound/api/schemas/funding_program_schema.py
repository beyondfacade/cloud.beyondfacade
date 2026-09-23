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
