"""시간대 보정 검증 — 구간 길이 차이를 지우지 않으면 결과가 통째로 뒤집힌다 (설계서 §3-1)."""

import pytest

from apps.metric.domain.services.quantiles import quantile
from apps.metric.domain.value_objects.hour_band import (
    band_intensities,
    block_intensities,
    flatness,
)


def test_24시간_균등이면_모든_구간의_시간강도가_1이다():
    uniform = {"00_06": 6, "06_11": 5, "11_14": 3, "14_17": 3, "17_21": 4, "21_24": 3}

    intensities = band_intensities(uniform)

    assert all(value == pytest.approx(1.0) for value in intensities.values())


def test_보정하지_않으면_가장_긴_구간이_이기지만_보정하면_뒤집힌다():
    # 00_06(6h) 원값이 11_14(3h)보다 크지만 시간당으로는 절반이다
    values = {"00_06": 120, "06_11": 50, "11_14": 90, "14_17": 30, "17_21": 40, "21_24": 30}

    assert max(values, key=lambda k: values[k]) == "00_06"
    assert max(band_intensities(values), key=lambda k: band_intensities(values)[k]) == "11_14"


def test_전체값이_0이면_빈_결과를_준다():
    assert band_intensities(dict.fromkeys(
        ["00_06", "06_11", "11_14", "14_17", "17_21", "21_24"], 0
    )) == {}
    assert block_intensities({}) == {}


def test_4블록_강도도_균등입력에서_1이다():
    uniform = {"00_06": 6, "06_11": 5, "11_14": 3, "14_17": 3, "17_21": 4, "21_24": 3}

    blocks = block_intensities(uniform)

    assert set(blocks) == {"morning", "day", "evening", "night"}
    assert all(value == pytest.approx(1.0) for value in blocks.values())
    assert flatness(blocks) == pytest.approx(1.0)


def test_밤_블록은_21_24와_00_06을_합친다():
    # 두 구간이 근접해 6구간 argmax가 동전 던지기가 되는 문제를 블록이 흡수한다 (설계서 §6-1)
    values = {"00_06": 60, "06_11": 10, "11_14": 5, "14_17": 5, "17_21": 10, "21_24": 30}

    blocks = block_intensities(values)

    assert max(blocks, key=lambda k: blocks[k]) == "night"


def test_평탄도는_바닥이_0이면_None이다():
    assert flatness({"morning": 2.0, "day": 0.0, "evening": 1.0, "night": 1.0}) is None


def test_분위수는_선형_보간이다():
    assert quantile([1, 2, 3, 4], 0.5) == pytest.approx(2.5)
    assert quantile([1, 2, 3, 4, 5], 0.25) == pytest.approx(2.0)
    assert quantile([], 0.5) is None
    assert quantile([7], 0.9) == 7
