from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class FundingProgram:
    """정책자금 공고 — 요약·메타데이터만 보유 (본문 전문 저장 금지, 원문 링크 필수).

    target_text·hashtags는 업종/지역 LLM 구조화 추출의 원천 — 원문 그대로 보존한다.
    """

    program_id: str  # 원천 공고 ID (bizinfo pblancId)
    source: str  # "bizinfo" — 소스 확장 대비
    title: str
    org: str  # 소관기관
    url: str  # 상세 원문 링크 (필수)
    apply_period: str  # 신청기간 원문 (예: "2026-09-03 ~ 2026-09-17", "상시")
    exec_org: str | None = None  # 수행기관
    field_category: str | None = None  # 지원분야 대분류
    field_subcategory: str | None = None  # 지원분야 중분류
    target_text: str | None = None  # 지원대상 원문
    hashtags: str | None = None  # 지역·업종 태그 원문
    apply_begin: date | None = None  # 파싱 실패·상시면 None
    deadline: date | None = None  # 파싱 실패·상시면 None
    summary: str | None = None  # 사업개요 발췌 (태그 제거)
    posted_at: datetime | None = None
    source_updated_at: datetime | None = None
    is_expired: bool = False

    def is_past_deadline(self, today: date) -> bool:
        """만료 판정 — 마감일이 있고 오늘보다 과거면 만료. 상시(None)는 만료 없음."""
        return self.deadline is not None and self.deadline < today
