"""interest_rate 적재 검증 — 실제 DB 업서트 멱등 (ON CONFLICT DO UPDATE)."""

from sqlalchemy import delete, select

from apps.shock.adapter.inbound.cli.load_interest_rate import upsert_rates
from apps.shock.adapter.outbound.orms.interest_rate_orm import InterestRateOrm
from apps.shock.domain.entities.interest_rate_entity import InterestRate
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_PREFIX = "test-rate:"


def _rate(period: str, rate: float) -> InterestRate:
    return InterestRate(
        id=f"{_TEST_PREFIX}{period}",
        rate_type="base",
        period=period,
        rate=rate,
        unit="연%",
        stat_code="722Y001",
        item_code="0101000",
    )


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(InterestRateOrm).where(InterestRateOrm.id.like(f"{_TEST_PREFIX}%"))
        )


def test_upsert_rates_is_idempotent_and_updates_value():
    _cleanup()
    assert upsert_rates([_rate("202001", 1.25), _rate("202002", 1.25)]) == 2
    assert upsert_rates([_rate("202001", 1.25)]) == 1  # 재실행 — PK 충돌 시 갱신
    # 정정 반영 — 같은 PK로 값이 바뀌면 최신값
    upsert_rates([_rate("202002", 0.75)])
    with session_scope() as session:
        stored = session.execute(
            select(InterestRateOrm.rate).where(
                InterestRateOrm.id == f"{_TEST_PREFIX}202002"
            )
        ).scalar_one()
    assert stored == 0.75
    _cleanup()
