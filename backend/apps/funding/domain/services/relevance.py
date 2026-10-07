"""질문 유사도 정렬 정책 — 규칙 필터를 통과한 후보만 다시 줄 세운다 (하이브리드 검색, LLM 없음).

자격 경계는 규칙 필터가 정한다. 여기서는 순서만 바꾼다 — 후보를 더하거나 빼지 않는다.
"""

from collections.abc import Sequence
from typing import TypeVar

ORDER_RELEVANCE = "relevance"  # 질문과 가까운 순
ORDER_DEADLINE = "deadline"  # 규칙 순서(마감 임박 순)

T = TypeVar("T")  # `.program.program_id`를 가진 후보(FundingCandidate·SupportItem)


def order_by_relevance(candidates: Sequence[T], ranked_ids: Sequence[str]) -> list[T]:
    """질문과 가까운 순(`ranked_ids`)으로 앞에 두고, 색인이 아직 없는 공고는 규칙 순서대로 뒤에 붙인다.

    `ranked_ids`에만 있는 id(후보 밖)는 무시한다. 정렬이 안정적이라 뒤에 붙는 공고는 규칙 순서를 지킨다.
    """
    position = {program_id: n for n, program_id in enumerate(ranked_ids)}
    unranked = len(position)
    return sorted(candidates, key=lambda c: position.get(c.program.program_id, unranked))
