"""업종×분기 서울 점포당 매출 중앙값 배치 러너 (Driving Adapter, CLI).

- 입력: 상권 원천(region_commerce_sales·region_commerce_store) 전 분기 + 업종-원천 코드 매핑 — 외부 API 호출 없음
- 산출: industry_sales_median_quarter 통째 재생성 — 재실행 멱등, 수 초
- 일일 크론(store-collector)의 build_metrics 다음에 돈다. 상권 원천을 손으로 다시 적재(load_commerce)해도 다음 새벽에 맞춰진다

실행: python -m apps.metric.adapter.inbound.cli.build_sales_median
"""

from apps.metric.dependencies.industry_sales_median_dependencies import (
    get_industry_sales_median_use_case,
)


def main() -> None:
    rows = get_industry_sales_median_use_case().build()
    print(f"서울 업종별 점포당 매출 중앙값: {rows}행 (업종×분기)")


if __name__ == "__main__":
    main()
