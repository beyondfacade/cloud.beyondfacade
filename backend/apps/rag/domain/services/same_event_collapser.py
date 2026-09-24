"""같은 사건 기사 접기 (Domain Service, 순수 함수).

뉴스 corpus는 같은 보도자료를 받은 기사가 3~50건씩 있다(2026-09-24 실측: 올리브영 남포 51건·신중앙시장 착공 34건).
그대로 두면 검색 top-5가 한 사건의 기사로 채워져 에이전트 컨텍스트가 낭비된다(뉴스 40문항 기준 top-5 중 평균 3건).
색인 시점이 아니라 검색 시점에 접는다 — 증분 크론에서 대표 기사가 흔들리지 않고, 재색인·스키마 변경이 없다.

판정: 제목(콘텐츠 첫 줄) 토큰 Jaccard ≥ 0.3 이고 보도일 차이 ≤ 3일이면 같은 사건. 점수 높은 기사가 대표로 남는다.
"""

import re
from collections.abc import Callable

from apps.rag.domain.entities.rag_chunk_entity import RagHit

_TOKEN = re.compile(r"[가-힣A-Za-z0-9]+")
_MIN_TOKEN_LEN = 2
_JACCARD_THRESHOLD = 0.3
_WINDOW_DAYS = 3


def _title_tokens(hit: RagHit) -> set[str]:
    title = hit.content.split("\n", 1)[0]
    return {t for t in _TOKEN.findall(title) if len(t) >= _MIN_TOKEN_LEN}


def same_event(a: RagHit, b: RagHit) -> bool:
    if a.published_at and b.published_at and abs((a.published_at - b.published_at).days) > _WINDOW_DAYS:
        return False
    ta, tb = _title_tokens(a), _title_tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) >= _JACCARD_THRESHOLD


def collapse_same_event(hits: list[RagHit]) -> list[RagHit]:
    """점수순 입력에서 앞선 대표와 같은 사건인 기사를 버린다. 순서는 유지."""
    kept: list[RagHit] = []
    for hit in hits:
        if not any(same_event(hit, rep) for rep in kept):
            kept.append(hit)
    return kept


Collapser = Callable[[list[RagHit]], list[RagHit]]
