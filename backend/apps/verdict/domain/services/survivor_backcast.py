"""부동산 생존자 역산 — 연도별 비율·동 분포 순수 계산 (업종 특화 신호 설계서 §10).
DB 읽기는 SurvivorBackcastGateway가 맡고, 여기는 그 결과를 받아 비율·분위수·표만 만든다."""

from collections.abc import Mapping, Sequence


def survivor_rows(
    survivors: Mapping[int, int], archive_opens: Mapping[int, int], years: Sequence[int]
) -> list[tuple[int, int, int, float | None]]:
    return [
        (y, survivors.get(y, 0), archive_opens.get(y, 0),
         None if not archive_opens.get(y) else survivors.get(y, 0) / archive_opens[y])
        for y in years
    ]


def ratio_quantiles(ratios: Sequence[float]) -> tuple[float, float, float]:
    ordered = sorted(ratios)
    pick = lambda p: ordered[int(p * (len(ordered) - 1))]  # noqa: E731
    return pick(0.1), pick(0.5), pick(0.9)


def render(
    rows: Sequence[tuple[int, int, int, float | None]],
    dong_quantiles: tuple[float, float, float],
    over_one: int,
    dong_count: int,
) -> str:
    lines = [
        "| 등록 연도 | 현재 영업 사무소 | 아카이브 개업 | 비율 |", "|---:|---:|---:|---:|",
        *[f"| {y} | {s:,} | {a:,} | {'—' if r is None else f'{r * 100:.1f}%'} |" for y, s, a, r in rows],
        "",
        f"동 단위(2021~2023 합산) 비율 p10 {dong_quantiles[0]:.2f} · 중위 {dong_quantiles[1]:.2f} · p90 {dong_quantiles[2]:.2f}, "
        f"비율 > 1인 동 {over_one}/{dong_count}",
    ]
    return "\n".join(lines)
