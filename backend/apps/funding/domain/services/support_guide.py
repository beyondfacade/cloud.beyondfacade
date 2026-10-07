"""창업 지원 정보 묶음 — 후보 공고를 대출·보증 / 우리 구 전용 / 창업·경영 셋으로 나눈다 (LLM 없음).

구청 공고도 소관기관이 `서울특별시`로 오는 일이 많다(2026-09-30 실측: 은평구 청년식당·관악구 원스톱 지원).
구 이름은 제목·태그에만 있어 거기서 찾는다. 다른 구 전용 공고는 그 구 사업자만 신청할 수 있어 뺀다.

업종은 제목·태그·지원대상에 업종 낱말이 있는지로만 본다 — 공고에 업종이 구조화돼 있지 않아 필터로 쓰지
않고 앞으로 올리는 가점과 "업종 관련" 표시에만 쓴다.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from apps.funding.domain.entities.funding_program_entity import FundingProgram
from apps.funding.domain.services.candidates import FundingCandidate, select_candidates

LOAN_FIELD = "금융"

_FOOD_WORDS: tuple[str, ...] = ("음식점", "외식", "식당", "식품접객", "요식")

# 업종 id → 공고 제목·태그에 나오는 낱말. 오탐이 나오면 여기만 고친다.
# 짧은 낱말은 남의 말에 섞인다("미용기기"·"헬스케어"·"대학원") — 업소를 가리키는 말까지 붙여 쓴다
INDUSTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "korean_food": _FOOD_WORDS,
    "chinese_food": _FOOD_WORDS,
    "japanese_food": _FOOD_WORDS,
    "western_food": _FOOD_WORDS,
    "snack": _FOOD_WORDS,
    "pub": (*_FOOD_WORDS, "주점"),
    "cafe": ("카페", "커피", "식품접객", "외식"),
    "convenience_store": ("편의점", "동네슈퍼", "소매점"),
    "hair_salon": ("미용실", "미용업", "이용업", "미용사"),
    "real_estate": ("부동산중개", "공인중개"),
    "karaoke": ("노래연습장", "노래방"),
    "pc_bang": ("PC방", "피시방"),
    "gym": ("헬스장", "체육시설", "피트니스"),
    "billiard": ("당구", "체육시설"),
    "academy": ("학원업", "교습소", "보습학원"),
    "childcare": ("어린이집", "보육"),
}

LOANS_LIMIT = 6
DISTRICT_LIMIT = 6
OTHERS_LIMIT = 8
SEARCH_LIMIT = 8  # 질문 검색 결과 — 묶음 구분 없이


@dataclass(frozen=True)
class SupportItem:
    """`why`는 후보 규칙 그대로다 — 우리 구·업종은 화면이 표시로 따로 달아 `why`에 겹쳐 쓰지 않는다."""

    candidate: FundingCandidate
    district_match: bool
    industry_match: bool

    @property
    def why(self) -> str:
        return self.candidate.why

    @property
    def program(self) -> FundingProgram:
        return self.candidate.program


@dataclass(frozen=True)
class SupportGuide:
    """`items`는 세 묶음으로 나누기 전 전체(규칙 순서) — 질문 검색이 이 경계 안에서만 정렬한다."""

    items: list[SupportItem] = field(default_factory=list)
    loans: list[SupportItem] = field(default_factory=list)
    district: list[SupportItem] = field(default_factory=list)
    others: list[SupportItem] = field(default_factory=list)


def _tags(hashtags: str | None) -> set[str]:
    return {tag.strip() for tag in (hashtags or "").split(",") if tag.strip()}


def mentioned_districts(program: FundingProgram, district_names: Iterable[str]) -> set[str]:
    """공고가 가리키는 서울 자치구 — 소관기관·태그는 낱말 그대로, 제목은 한글 낱말 첫머리에서만 찾는다.

    제목의 앞 글자를 보는 까닭은 "집중구역"의 "중구" 같은 오탐을 막기 위해서다.
    """
    tags = _tags(program.hashtags)
    org = (program.org or "").strip()
    return {
        name
        for name in district_names
        if name == org
        or name in tags
        or re.search(rf"(?<![가-힣]){re.escape(name)}", program.title)
    }


def open_to_district(program: FundingProgram, district_names: Iterable[str], district_name: str | None) -> bool:
    """구 전용이 아니거나 우리 구 전용인 공고 — 구를 모르면(`None`) 구 전용은 모두 닫혀 있다."""
    districts = mentioned_districts(program, district_names)
    return not districts or district_name in districts


def industry_matched(program: FundingProgram, industry_id: str | None) -> bool:
    words = INDUSTRY_KEYWORDS.get(industry_id or "", ())
    blob = f"{program.title} {program.hashtags or ''} {program.target_text or ''}"
    return any(word in blob for word in words)


def build_support_guide(
    programs: Iterable[FundingProgram],
    *,
    seoul_district_names: Iterable[str],
    district_name: str | None,
    industry_id: str | None,
    today: date,
) -> SupportGuide:
    """후보 선별(서울·전국 ∩ 소상공인·창업 대상, 미만료) 뒤 다른 구 전용을 빼고 세 묶음으로 나눈다.

    금융 분야는 구 전용이어도 대출 묶음에 둔다 — 대출을 찾는 사람이 한곳에서 비교하게 하려고.
    묶음 안 순서는 후보 선별 순서를 유지하되 대출은 우리 구, 나머지는 업종 관련을 앞으로 올린다.
    """
    names = frozenset(seoul_district_names)
    program_list = list(programs)
    ranked = select_candidates(
        program_list, seoul_district_names=names, today=today, limit=len(program_list)
    )
    items: list[SupportItem] = []
    for candidate in ranked:
        if not open_to_district(candidate.program, names, district_name):
            continue
        items.append(
            SupportItem(
                candidate,
                district_match=bool(mentioned_districts(candidate.program, names)),
                industry_match=industry_matched(candidate.program, industry_id),
            )
        )

    loans = [item for item in items if item.candidate.program.field_category == LOAN_FIELD]
    rest = [item for item in items if item.candidate.program.field_category != LOAN_FIELD]
    by_industry = lambda item: not item.industry_match  # noqa: E731
    return SupportGuide(
        items=items,
        loans=sorted(loans, key=lambda item: not item.district_match)[:LOANS_LIMIT],
        district=sorted((i for i in rest if i.district_match), key=by_industry)[:DISTRICT_LIMIT],
        others=sorted((i for i in rest if not i.district_match), key=by_industry)[:OTHERS_LIMIT],
    )
