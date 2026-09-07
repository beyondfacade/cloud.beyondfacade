"""한국은행 기준금리 적재 러너 (Driving Adapter, CLI — 주 1회 크론 실행 대상).

ECOS StatisticSearch 722Y001(월)/0101000, 2019-01~현재 1회 호출 전량 수신 →
interest_rate 업서트(PK 충돌 시 갱신 — 멱등). load_population 관행(ORM 직접 업서트).

실행: python -m apps.shock.adapter.inbound.cli.load_interest_rate
"""

from dataclasses import asdict

from sqlalchemy.dialects.postgresql import insert

from apps.shock.adapter.outbound.gateways.ecos_gateway import EcosBaseRateGateway
from apps.shock.adapter.outbound.orms.interest_rate_orm import InterestRateOrm
from apps.shock.domain.entities.interest_rate_entity import InterestRate
from core.matrix.grid_oracle_database_manager import session_scope


def upsert_rates(rates: list[InterestRate]) -> int:
    """PK(id) 충돌 시 값 갱신 — 재실행 멱등. 처리 행 수 반환."""
    if not rates:
        return 0
    with session_scope() as session:
        statement = insert(InterestRateOrm).values([asdict(rate) for rate in rates])
        session.execute(
            statement.on_conflict_do_update(
                index_elements=["id"],
                set_={"rate": statement.excluded.rate, "unit": statement.excluded.unit},
            )
        )
    return len(rates)


def main() -> None:
    rates = EcosBaseRateGateway().fetch_rates()
    count = upsert_rates(rates)
    changes = [
        f"{cur.period} {prev.rate:g}→{cur.rate:g}%"
        for prev, cur in zip(rates, rates[1:])
        if prev.rate != cur.rate
    ]
    print(f"interest rate loader: {count}행 업서트 / 변경점 {len(changes)}건")
    print(" | ".join(changes))


if __name__ == "__main__":
    main()
