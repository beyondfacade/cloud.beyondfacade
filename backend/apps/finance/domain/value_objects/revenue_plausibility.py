"""프리필 월매출을 믿을 수 없는 경우 — 채우지 않고 이유를 단서로 준다 (2026-10-06 사용자 결정 A).

원천(서울시 추정매출)은 카드 결제 기반 추정이라 현금·계좌이체 비중이 큰 업종·동은 매출이 적게 잡히는데,
분모(점포 수)에는 등록 점포가 전부 들어간다. 실측(2025년 4분기): 가양제1동 미용실 428곳 월 약 67만 원,
부동산중개업은 서울 동 중앙값이 월 22만 원. 규칙은 앞에서부터 처음 걸린 것의 이유를 쓴다.
"""

from collections.abc import Callable

# 중개보수는 카드 매출로 거의 잡히지 않는다 — 동과 무관하게 업종 전체가 잴 수 없다
_CARD_UNMEASURABLE: dict[str, str] = {
    "real_estate": "부동산 중개보수는 카드 매출로 거의 잡히지 않아 이 자료로 월매출을 추정할 수 없습니다.",
}

# 서울 같은 업종 동 중앙값의 1/3 미만 — 높은 쪽은 번화가 실측(역삼1동 카페 중앙값의 약 3.8배)이라 두지 않는다
LOW_RATIO_TO_SEOUL_MEDIAN = 1 / 3

_ASK = " 예상 월매출을 직접 넣으세요."


def _card_unmeasurable(industry_id: str, per_store: float, seoul_median: float | None) -> str | None:
    return _CARD_UNMEASURABLE.get(industry_id)


def _far_below_seoul(industry_id: str, per_store: float, seoul_median: float | None) -> str | None:
    if seoul_median is None or per_store >= seoul_median * LOW_RATIO_TO_SEOUL_MEDIAN:
        return None
    return (
        "이 동은 매출 자료를 믿기 어렵습니다 — 점포당 평균이 서울 같은 업종 동 중앙값의 3분의 1에도 못 미칩니다"
        "(카드로 잡히지 않는 매출이 많을 수 있습니다)."
    )


_RULES: tuple[Callable[[str, float, float | None], str | None], ...] = (_card_unmeasurable, _far_below_seoul)


def implausible_revenue_reason(industry_id: str, per_store: float, seoul_median: float | None) -> str | None:
    """믿을 수 없으면 사용자에게 보일 이유(직접 입력 안내 포함), 아니면 None. 두 값은 같은 단위(점포당 분기 매출)."""
    for rule in _RULES:
        reason = rule(industry_id, per_store, seoul_median)
        if reason is not None:
            return reason + _ASK
    return None
