"""법정동 → 행정동 배분 (업종 특화 신호 설계서 §11-3). 순수 파이썬 — 근사: 같은 법정동 상가의 행정동 분포 비율로 나눈다."""

import re
from collections.abc import Mapping
from datetime import date

_LEGAL_DONG = re.compile(r"^서울(?:특별)?시\s+\S+구\s+(\S+?(?:동|가))(?:\s|$)")


def legal_dong_of(jibun_address: str | None) -> str | None:
    match = _LEGAL_DONG.match(jibun_address.strip()) if jibun_address else None
    return match.group(1) if match else None


def allocate(
    trades: Mapping[tuple[str, str], int], weights: Mapping[tuple[str, str], Mapping[str, int]]
) -> dict[str, float]:
    """(구, 법정동) 건수를 그 법정동 상가의 행정동 분포 비율로 나눈다. 분포가 없는 법정동은 버린다."""
    result: dict[str, float] = {}
    for key, count in trades.items():
        shares = weights.get(key, {})
        total = sum(shares.values())
        for region, weight in shares.items():
            result[region] = result.get(region, 0.0) + count * weight / total
    return result


def month_window(today: date, months: int = 12, lag: int = 2) -> tuple[str, str]:
    """기준월 lag개월 전까지 months개월 — 신고기한(30일) 탓에 최근 월은 미완결 (api.md 국토부 실거래가)."""
    last = today.year * 12 + today.month - 1 - lag
    first = last - months + 1
    return f"{first // 12}{first % 12 + 1:02d}", f"{last // 12}{last % 12 + 1:02d}"
