"""분위수 — 판정 임계값은 매 배치 그 창의 분포에서 다시 계산한다 (설계서 §3, 하드코딩 금지).

절대값으로 굳히면 "서울 안에서의 상대 위치"라는 뜻이 사라진다. 분류 문서의 수치(1.491 등)는
확인용이지 상수가 아니다.
"""

from collections.abc import Iterable


def quantile(values: Iterable[float], q: float) -> float | None:
    """선형 보간 분위수 (numpy 기본과 동일). 값이 없으면 None."""
    ordered = sorted(values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)
