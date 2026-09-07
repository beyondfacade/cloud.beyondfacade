"""만료 판정 검증 — 엔티티 규칙 + Repository 일 배치 갱신(만료·연장 복원·상시)."""

from datetime import date

from sqlalchemy import delete, select

from apps.funding.adapter.outbound.orm_mappers.funding_program_orm_mapper import to_orm
from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
from apps.funding.adapter.outbound.repositories.funding_program_repository import (
    SqlAlchemyFundingProgramRepository,
)
from apps.funding.domain.entities.funding_program_entity import FundingProgram
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_PREFIX = "test-fundexp-"
_TODAY = date(2026, 9, 7)


def _program(n: int, deadline: date | None, is_expired: bool = False) -> FundingProgram:
    return FundingProgram(
        program_id=f"{_TEST_PREFIX}{n}",
        source="bizinfo",
        title=f"공고 {n}",
        org="기관",
        url=f"https://example.com/{_TEST_PREFIX}{n}",
        apply_period="",
        deadline=deadline,
        is_expired=is_expired,
    )


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(FundingProgramOrm).where(
                FundingProgramOrm.program_id.like(f"{_TEST_PREFIX}%")
            )
        )


def test_entity_is_past_deadline():
    assert _program(0, date(2026, 9, 6)).is_past_deadline(_TODAY) is True
    assert _program(0, _TODAY).is_past_deadline(_TODAY) is False  # 마감 당일은 미만료
    assert _program(0, None).is_past_deadline(_TODAY) is False  # 상시


def test_refresh_expirations_flags_restores_and_keeps_always_open():
    _cleanup()
    with session_scope() as session:
        session.add(to_orm(_program(1, date(2026, 9, 6))))  # 마감 지남 → 만료 대상
        session.add(to_orm(_program(2, _TODAY)))  # 당일 → 유지
        session.add(to_orm(_program(3, None)))  # 상시 → 유지
        session.add(to_orm(_program(4, date(2026, 10, 1), is_expired=True)))  # 연장 → 복원

    repository = SqlAlchemyFundingProgramRepository()
    assert repository.refresh_expirations(_TODAY) == 1  # 신규 만료는 1건뿐
    assert repository.refresh_expirations(_TODAY) == 0  # 재실행 멱등

    with session_scope() as session:
        flags = dict(
            session.execute(
                select(FundingProgramOrm.program_id, FundingProgramOrm.is_expired).where(
                    FundingProgramOrm.program_id.like(f"{_TEST_PREFIX}%")
                )
            ).all()
        )
    assert flags[f"{_TEST_PREFIX}1"] is True
    assert flags[f"{_TEST_PREFIX}2"] is False
    assert flags[f"{_TEST_PREFIX}3"] is False
    assert flags[f"{_TEST_PREFIX}4"] is False
    _cleanup()
