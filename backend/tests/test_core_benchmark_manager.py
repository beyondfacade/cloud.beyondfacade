"""모델 평가 공통 통계 — rag·agent·intent 하네스가 함께 쓴다."""

import pytest

from core.matrix.grid_benchmark_manager import paired_bootstrap_ci, percentile, pick_winner, resident_models


def test_bootstrap_같은_점수면_0():
    assert paired_bootstrap_ci([1.0, 0.5], [1.0, 0.5]) == (0.0, 0.0, 0.0)


def test_bootstrap_길이가_다르면_에러():
    with pytest.raises(ValueError):
        paired_bootstrap_ci([1.0], [1.0, 0.0])


def test_백분위():
    assert percentile([10.0, 20.0, 30.0], 50) == 20.0


def test_상주_모델():
    assert resident_models({"models": [{"name": "bge-m3:latest"}]}) == {"bge-m3:latest"}


def test_동률이면_비용이_작은_쪽():
    s = {"big": [1.0, 0.5] * 20, "small": [1.0, 0.5] * 20}
    winner, tied = pick_winner(s, {"big": 7600, "small": 1900}, {}, ["big", "small"])
    assert winner == "small" and tied == ["big", "small"]


def test_유의하게_높으면_비용이_커도_이긴다():
    s = {"big": [1.0] * 40, "small": [0.5] * 40}
    assert pick_winner(s, {"big": 7600, "small": 1900}, {}, ["big", "small"])[0] == "big"
