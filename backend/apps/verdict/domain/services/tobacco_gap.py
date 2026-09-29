"""담배권 빈자리 — 상가 자리 중 영업 중인 담배소매인 반경 안에 든 비율 (업종 특화 신호 설계서 §6). 순수 파이썬 격자 근접 판정."""

import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

# 반경 50m — 소매인 간격 실측(9/29): 100m 안 이웃 73%라 100m 제한 구는 드물고, 100m로 재면 동 중위 95%가 막혀
# 변별력이 없다(설계서 §2-2·§3). 구별 조례 반영은 후속 — 바꿀 때는 이 상수 한 곳.
TOBACCO_GAP_RADIUS_M = 50.0

_M_PER_DEG_LAT = 111_320.0
_M_PER_DEG_LNG = 111_320.0 * math.cos(math.radians(37.55))  # 서울 기준 등장방형 근사


@dataclass(frozen=True)
class GeoPoint:
    region_code: str | None
    lat: float
    lng: float


def _xy(point: GeoPoint) -> tuple[float, float]:
    return point.lat * _M_PER_DEG_LAT, point.lng * _M_PER_DEG_LNG


def blocked_counts(
    candidates: Iterable[GeoPoint], retailers: Iterable[GeoPoint], radius_m: float = TOBACCO_GAP_RADIUS_M
) -> dict[str, tuple[int, int]]:
    """동별 (후보 자리 수, 반경 안에 소매인이 하나라도 있는 자리 수). 격자 한 칸 = 반경이라 이웃 9칸만 본다."""
    grid: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)
    for retailer in retailers:
        x, y = _xy(retailer)
        grid[(int(x // radius_m), int(y // radius_m))].append((x, y))
    totals: dict[str, list[int]] = {}
    for candidate in candidates:
        if candidate.region_code is None:
            continue
        x, y = _xy(candidate)
        cx, cy = int(x // radius_m), int(y // radius_m)
        near = any(
            math.hypot(x - rx, y - ry) <= radius_m
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            for rx, ry in grid.get((cx + dx, cy + dy), ())
        )
        cell = totals.setdefault(candidate.region_code, [0, 0])
        cell[0] += 1
        cell[1] += near
    return {region: (total, blocked) for region, (total, blocked) in totals.items()}
