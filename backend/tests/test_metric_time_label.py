"""시간대 서사 라벨 검증 — 4블록 평탄도 우선, 그다음 정점 블록 (분류 문서 §6)."""

import pytest

from apps.metric.domain.services.time_label import (
    TimeLabelInput,
    derive_flatness_threshold,
    label_time,
)

_UNIFORM = {"00_06": 6, "06_11": 5, "11_14": 3, "14_17": 3, "17_21": 4, "21_24": 3}


def _input(values) -> TimeLabelInput:
    return TimeLabelInput(hour_values=values)


def test_평탄도가_하한_미만이면_정점과_무관하게_평탄이다():
    result = label_time(_input(_UNIFORM), flatness_threshold=1.152)

    assert result.time_label == "flat"


def test_평탄하지_않으면_정점_블록이_라벨이_된다():
    values = {"00_06": 60, "06_11": 5, "11_14": 3, "14_17": 3, "17_21": 5, "21_24": 30}

    result = label_time(_input(values), flatness_threshold=1.152)

    assert result.time_label == "night"
    assert result.peak_block == "night"


def test_정점과_바닥은_평탄한_동에서도_계산된다():
    # 라벨이 flat이어도 phases 슬롯이 정점·바닥 쌍을 쓴다 (분류 문서 §6-4)
    result = label_time(_input(_UNIFORM), flatness_threshold=99.0)

    assert result.time_label == "flat"
    assert result.peak_block in {"morning", "day", "evening", "night"}
    assert result.trough_block in {"morning", "day", "evening", "night"}


def test_업무_밀집형_모양은_낮_정점_밤_바닥이_된다():
    values = {"00_06": 3, "06_11": 20, "11_14": 30, "14_17": 28, "17_21": 15, "21_24": 4}

    result = label_time(_input(values), flatness_threshold=1.152)

    assert result.time_label == "day"
    assert (result.peak_block, result.trough_block) == ("day", "night")


def test_값이_없으면_라벨을_만들지_않는다():
    result = label_time(_input(dict.fromkeys(_UNIFORM, 0)), flatness_threshold=1.152)

    assert result.time_label is None
    assert result.peak_block is None and result.trough_block is None


def test_평탄도_하한은_창의_분포에서_계산된다():
    values = [
        {"00_06": 6, "06_11": 5, "11_14": 3, "14_17": 3, "17_21": 4, "21_24": 3},
        {"00_06": 12, "06_11": 5, "11_14": 3, "14_17": 3, "17_21": 4, "21_24": 3},
        {"00_06": 30, "06_11": 5, "11_14": 3, "14_17": 3, "17_21": 4, "21_24": 3},
        {"00_06": 60, "06_11": 5, "11_14": 3, "14_17": 3, "17_21": 4, "21_24": 3},
    ]

    threshold = derive_flatness_threshold([_input(v) for v in values])

    assert threshold is not None and threshold == pytest.approx(1.5)
