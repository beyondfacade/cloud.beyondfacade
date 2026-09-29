"""부동산 생존자 역산 — 연도별 비율·동 분포 (업종 특화 신호 설계서 §10)."""

from apps.verdict.domain.services.survivor_backcast import ratio_quantiles, render, survivor_rows


def test_연도별_비율은_생존_사무소를_아카이브_개업으로_나누고_0이면_None이다():
    rows = survivor_rows({2021: 1500, 2024: 1550}, {2021: 5000, 2024: 0}, [2021, 2024])
    assert rows == [(2021, 1500, 5000, 0.3), (2024, 1550, 0, None)]


def test_분위수는_정렬한_값의_인덱스로_뽑는다():
    assert ratio_quantiles([0.5, 0.1, 0.3, 0.9, 0.7]) == (0.1, 0.5, 0.7)


def test_표는_연도와_비율을_찍는다():
    text = render([(2021, 1500, 5000, 0.3), (2024, 1550, 0, None)], (0.1, 0.3, 0.6), 4, 420)
    assert "| 2021 | 1,500 | 5,000 | 30.0% |" in text and "| 2024 | 1,550 | 0 | — |" in text
    assert "비율 > 1인 동 4/420" in text
