"""부동산 생존자 역산 — 현재 영업 사무소의 등록 연도별 수 ÷ 상권분석 아카이브 같은 연도 개업 수 (업종 특화 신호 설계서 §10).
분석 전용(읽기만). 비율 ≈ 그 연도 개업의 현재 생존율 × (스냅샷 포착률 ÷ 아카이브 포착률). 2024~는 아카이브 개업 단절(설계서 §2-3).
DB 읽기는 SurvivorBackcastGateway에서만(컨트롤러 P6) — 이 파일은 게이트웨이 호출과 표 출력만 한다.

    cd backend && .venv/bin/python -m apps.verdict.adapter.inbound.cli.real_estate_survivor_backcast
"""

from apps.verdict.adapter.outbound.gateways.survivor_backcast_gateway import SurvivorBackcastGateway
from apps.verdict.domain.services.survivor_backcast import ratio_quantiles, render, survivor_rows

_YEARS = (2021, 2022, 2023, 2024, 2025)
_DONG_YEARS = (2021, 2022, 2023)  # 아카이브 개업이 살아 있는 연도만 동 분포에


def main() -> None:
    data = SurvivorBackcastGateway().fetch(_YEARS, _DONG_YEARS)
    ratios = [data.dong_survivors.get(r, 0) / n for r, n in data.dong_archive_opens.items() if n]
    print(
        render(
            survivor_rows(data.survivors_by_year, data.archive_opens_by_year, _YEARS),
            ratio_quantiles(ratios),
            sum(1 for x in ratios if x > 1),
            len(ratios),
        )
    )


if __name__ == "__main__":
    main()
