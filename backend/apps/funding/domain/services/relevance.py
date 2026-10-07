"""질문 유사도 정렬 정책 — 규칙 필터를 통과한 후보만 다시 줄 세운다 (하이브리드 검색, LLM 없음).

자격 경계는 규칙 필터가 정한다. 여기서는 순서만 바꾼다 — 후보를 더하거나 빼지 않는다.
"""

from collections.abc import Sequence
from typing import TypeVar

ORDER_RELEVANCE = "relevance"  # 질문과 가까운 순
ORDER_DEADLINE = "deadline"  # 규칙 순서(마감 임박 순)

# 유사도 기준선 — bge-m3 코사인 거리 `d ≤ min(MAX_DISTANCE, 1등 거리 + MAX_GAP)`만 "질문과 관련 있음".
# 10/7 실측(질문 8개 × 자격 통과 74건): 짧은 질문은 전체가 가깝고(중앙값 0.50) 구체적 질문은 1등만
# 가까워 절대값 하나로는 못 가른다 → 절대 상한 + 1등과의 차이. 평가셋 자격 정답 6/6 기준 안 유지.
MAX_DISTANCE = 0.54
MAX_GAP = 0.08

T = TypeVar("T")  # `.program.program_id`를 가진 후보(FundingCandidate·SupportItem)


def relevant_ids(
    scored: Sequence[tuple[str, float]],
    max_distance: float = MAX_DISTANCE,
    max_gap: float = MAX_GAP,
) -> list[str]:
    """기준선을 통과한 id만 가까운 순으로 — `scored`는 (id, 거리) 가까운 순."""
    if not scored:
        return []
    limit = min(max_distance, scored[0][1] + max_gap)
    return [program_id for program_id, distance in scored if distance <= limit]


def order_by_relevance(candidates: Sequence[T], ranked_ids: Sequence[str]) -> list[T]:
    """질문과 가까운 순(`ranked_ids`)으로 앞에 두고, 기준선 밖·색인 없는 공고는 규칙 순서대로 뒤에 붙인다.

    `ranked_ids`에만 있는 id(후보 밖)는 무시한다. 정렬이 안정적이라 뒤에 붙는 공고는 규칙 순서를 지킨다.
    """
    position = {program_id: n for n, program_id in enumerate(ranked_ids)}
    unranked = len(position)
    return sorted(candidates, key=lambda c: position.get(c.program.program_id, unranked))
