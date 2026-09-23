"""후보 공고 선별 — 결정론 필터·정렬, LLM 없음 (설계서 §3).

상품 목록이 아니라 "상담에서 물어볼 만한 것"의 후보다. 자격 확정이 아니며 그 사실은 화면이 말한다.

필터에 쓰지 않는 것 둘 — 있는 척하지 않기 위해서다.
- `external_funding_need`: 공고에 한도가 구조화돼 있지 않다. 응답에 되돌리기만 한다
- `industry_id`: 공고의 업종 정보가 `target_text`·`hashtags` 원문뿐이라 신뢰할 만한 매칭이 안 된다.
  역시 응답에 되돌리기만 한다 (구조화는 T4-3)
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from apps.funding.domain.entities.funding_program_entity import FundingProgram
from apps.funding.domain.services.region_filter import (
    REGION_LABELS,
    REGION_NATIONWIDE,
    REGION_SEOUL,
    classify_region,
)

# 긴 것부터 — "예비창업"이 "창업"보다 먼저 잡혀야 라벨이 정확하다
AUDIENCE_KEYWORDS: tuple[str, ...] = ("예비창업", "소상공인", "창업")

PRIORITY_FIELDS: tuple[str, ...] = ("금융", "창업", "경영")

STAGE_PRE = "pre"  # 사업자등록 전
STAGE_REGISTERED = "registered"

# 창업 단계별 가점 — 필터가 아니라 정렬 가점이다. 해당 없는 단계는 그냥 0
_STAGE_BONUS: dict[str, dict[str, int]] = {
    STAGE_PRE: {"예비창업": 2, "창업": 1},
    STAGE_REGISTERED: {"소상공인": 2},
}

_REGION_ORDER: dict[str, int] = {REGION_SEOUL: 0, REGION_NATIONWIDE: 1}

DEFAULT_LIMIT = 8


@dataclass(frozen=True)
class FundingCandidate:
    program: FundingProgram
    region: str  # seoul | nationwide
    audience: str  # 예비창업 | 소상공인 | 창업
    field_priority: bool
    why: str


def _audience_of(program: FundingProgram) -> str | None:
    """대상 — `target_text` 우선, 없으면 제목. 원천이 대상을 비워두는 공고가 많다."""
    blob = f"{program.target_text or ''} {program.title}"
    return next((word for word in AUDIENCE_KEYWORDS if word in blob), None)


def _why(region: str, audience: str, field_priority: bool, field_category: str | None) -> str:
    parts = [REGION_LABELS[region], audience]
    # 대상과 분야가 같은 말이면("창업 · 창업") 한 번만 쓴다
    if field_priority and field_category and field_category != audience:
        parts.append(field_category)
    return " · ".join(parts)


def _sort_key(candidate: FundingCandidate, stage: str | None) -> tuple:
    bonus = _STAGE_BONUS.get(stage or "", {}).get(candidate.audience, 0)
    program = candidate.program
    return (
        _REGION_ORDER[candidate.region],  # 서울 전용 → 전국
        0 if candidate.field_priority else 1,  # 금융·창업·경영 우선
        -bonus,  # 창업 단계 가점
        program.deadline is None,  # 상시는 뒤
        program.deadline or "",  # 마감 임박 순
        program.program_id,  # 동률에서도 결과가 흔들리지 않게
    )


def select_candidates(
    programs: Iterable[FundingProgram],
    *,
    seoul_district_names: Iterable[str],
    today: date,
    stage: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[FundingCandidate]:
    """미만료 공고에서 서울·전국 ∩ 소상공인·창업 대상만 남겨 정렬 상위 `limit`건.

    만료는 `is_expired` 플래그와 `deadline` **둘 다** 본다. 플래그는 일 배치
    (`refresh_expirations`)가 갱신하므로 배치가 늦으면 마감 지난 공고가 남아 있다 — 상담 자료에
    지난 공고를 넣는 것은 그 자체로 결함이다.
    """
    district_names = frozenset(seoul_district_names)
    matched: list[FundingCandidate] = []
    for program in programs:
        if program.is_expired or program.is_past_deadline(today):
            continue
        region = classify_region(program.hashtags, program.org, district_names)
        if region is None:
            continue
        audience = _audience_of(program)
        if audience is None:
            continue
        field_priority = program.field_category in PRIORITY_FIELDS
        matched.append(
            FundingCandidate(
                program=program,
                region=region,
                audience=audience,
                field_priority=field_priority,
                why=_why(region, audience, field_priority, program.field_category),
            )
        )
    matched.sort(key=lambda candidate: _sort_key(candidate, stage))
    return matched[:limit]


def candidate_titles(candidates: Sequence[FundingCandidate], count: int) -> list[str]:
    """확인할 질문이 인용할 상위 제목 — 화면이 finance BC로 실어 보낸다."""
    return [candidate.program.title for candidate in candidates[:count]]
