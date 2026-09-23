"""시간대 서사 라벨 — 4블록 평탄도가 먼저, 그다음 정점 블록 (분류 문서 §6).

6구간 argmax를 그대로 쓰면 조합이 16종으로 흩어지고 하위 조합은 1~5개 동짜리라 쓸모가 없다.
더 나쁜 것은 `00_06`과 `21_24`가 근접해 argmax가 동전 던지기가 된다는 점이다 — 둘 다 "밤에
사람이 집에 있다"는 같은 뜻인데 판정이 갈린다. 4블록이 그 둘을 하나로 흡수한다.

라벨은 반드시 4분기 이동평균으로만 쓴다. 분기 단독 안정성은 60.0%에 그친다 (분류 문서 §6-6).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from apps.metric.domain.services.quantiles import quantile
from apps.metric.domain.value_objects.hour_band import (
    TIME_BLOCKS,
    block_intensities,
    flatness,
)


@dataclass(frozen=True)
class TimeLabelInput:
    hour_values: Mapping[str, float]  # 6구간 원값 — 보정은 내부에서 한다


@dataclass(frozen=True)
class TimeLabelResult:
    time_label: str | None  # morning | day | evening | night | flat
    peak_block: str | None
    trough_block: str | None


def derive_flatness_threshold(inputs: Sequence[TimeLabelInput]) -> float | None:
    """평탄 경계 = 창의 평탄도 분포 하위 25%. 하드코딩 금지 (설계서 §3)."""
    values = [
        value
        for candidate in inputs
        if (value := flatness(block_intensities(candidate.hour_values))) is not None
    ]
    return quantile(values, 0.25)


def label_time(candidate: TimeLabelInput, flatness_threshold: float | None) -> TimeLabelResult:
    intensities = block_intensities(candidate.hour_values)
    if not intensities:
        return TimeLabelResult(time_label=None, peak_block=None, trough_block=None)
    # 동점은 블록 선언 순서로 깬다 — 배치를 다시 돌려도 같은 값이 나와야 한다
    order = list(TIME_BLOCKS)
    peak = min(order, key=lambda block: (-intensities[block], order.index(block)))
    trough = min(order, key=lambda block: (intensities[block], order.index(block)))
    spread = flatness(intensities)
    is_flat = (
        spread is not None and flatness_threshold is not None and spread < flatness_threshold
    )
    return TimeLabelResult(
        time_label="flat" if is_flat else peak,
        peak_block=peak,
        trough_block=trough,
    )
