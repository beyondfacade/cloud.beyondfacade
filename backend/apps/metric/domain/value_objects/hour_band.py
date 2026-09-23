"""시간대 6구간과 4블록 — profile·hour_gap 두 프랙탈이 횡단 공유하는 VO (CLAUDE.md §12 AOP 예외).

원천 6구간은 길이가 다르다(6·5·3·3·4·3시간). 원값을 그대로 비교하면 긴 구간이 무조건 이겨
425개 동 중 377개가 `00_06` 최대로 나온다(설계서 §3-1). 유동인구와 매출 분해가 같은 6구간을
쓰므로 양쪽에 똑같이 적용한다.
"""

from collections.abc import Mapping

HOUR_BANDS: tuple[str, ...] = ("00_06", "06_11", "11_14", "14_17", "17_21", "21_24")

# 구간 길이(시간) — 합 24
_BAND_HOURS: dict[str, int] = {
    "00_06": 6,
    "06_11": 5,
    "11_14": 3,
    "14_17": 3,
    "17_21": 4,
    "21_24": 3,
}

# 4블록 — 6구간 argmax는 16종으로 흩어지고 `00_06`·`21_24`가 근접해 동전 던지기가 된다(설계서 §6-2)
TIME_BLOCKS: dict[str, tuple[str, ...]] = {
    "morning": ("06_11",),
    "day": ("11_14", "14_17"),
    "evening": ("17_21",),
    "night": ("21_24", "00_06"),
}

_BLOCK_HOURS: dict[str, int] = {
    block: sum(_BAND_HOURS[band] for band in bands) for block, bands in TIME_BLOCKS.items()
}


def band_intensities(values: Mapping[str, float]) -> dict[str, float]:
    """구간값 → 시간당 강도. 1.0이 24시간 균등.

    시간강도 = 구간값 ÷ 구간길이 ÷ (전체값 ÷ 24). 전체값이 0 이하면 빈 dict.
    """
    total = sum(values.get(band, 0.0) for band in HOUR_BANDS)
    if total <= 0:
        return {}
    return {
        band: (values.get(band, 0.0) / _BAND_HOURS[band]) / (total / 24)
        for band in HOUR_BANDS
    }


def block_intensities(values: Mapping[str, float]) -> dict[str, float]:
    """구간값 → 4블록 시간당 강도. 블록강도 = (블록 비중 합 ÷ 블록 시간) × 24."""
    total = sum(values.get(band, 0.0) for band in HOUR_BANDS)
    if total <= 0:
        return {}
    return {
        block: (sum(values.get(band, 0.0) for band in bands) / total)
        / _BLOCK_HOURS[block]
        * 24
        for block, bands in TIME_BLOCKS.items()
    }


def flatness(block_intensity: Mapping[str, float]) -> float | None:
    """평탄도 = max(블록강도) ÷ min(블록강도). 바닥이 0이거나 값이 없으면 None."""
    if not block_intensity:
        return None
    low = min(block_intensity.values())
    if low <= 0:
        return None
    return max(block_intensity.values()) / low
