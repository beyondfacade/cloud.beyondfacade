"""ECOS 가중평균 대출금리 적재 러너 (Driving Adapter, CLI — 주 1회 크론 실행 대상).

121Y006(신규취급액 기준) 기업·중소기업·시설자금 3계열, 2019-01~현재 월별 →
interest_rate 업서트(멱등, load_interest_rate.upsert_rates 재사용).
COFIX(은행연합회) 원천이 robots.txt 전면 불허라 정식 API인 121Y006으로 대체 (v0.16.0).

실행: python -m apps.shock.adapter.inbound.cli.load_loan_rate
"""

from apps.shock.adapter.inbound.cli.load_interest_rate import upsert_rates
from apps.shock.adapter.outbound.gateways.ecos_gateway import (
    LOAN_SERIES,
    EcosLoanRateGateway,
)


def main() -> None:
    rates = EcosLoanRateGateway().fetch_rates()
    count = upsert_rates(rates)
    print(f"loan rate loader: {count}행 업서트")
    for series in LOAN_SERIES:
        periods = sorted(r.period for r in rates if r.rate_type == series.rate_type)
        if periods:
            print(f"  {series.rate_type}: {len(periods)}행 {periods[0]}~{periods[-1]}")


if __name__ == "__main__":
    main()
