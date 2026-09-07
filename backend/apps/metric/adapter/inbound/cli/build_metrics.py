"""지역×업종 연도별 지표 배치 러너 (Driving Adapter, CLI).

- 입력: store 테이블의 region_code 보유분만 읽는다 — 외부 API 호출 없음
- 산출: region_industry_metric (행정동×업종×연도 2019~2026) 업서트 — 재실행 멱등
- 일일 증분 크론(store-collector)의 assign_regions 후속 실행을 전제로 설계

실행: python -m apps.metric.adapter.inbound.cli.build_metrics
"""

from apps.metric.dependencies.region_industry_metric_dependencies import (
    get_region_industry_metric_use_case,
)

_YEARS = list(range(2019, 2027))


def main() -> None:
    processed = get_region_industry_metric_use_case().build(_YEARS)
    print(f"지표 업서트: {processed}건 (연도 {_YEARS[0]}~{_YEARS[-1]})")


if __name__ == "__main__":
    main()
