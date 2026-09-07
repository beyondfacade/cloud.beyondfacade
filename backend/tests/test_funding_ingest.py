"""funding ingest 검증 — Fake 게이트웨이(경계 모킹) + 실제 Repository/DB 업서트 멱등."""

from datetime import date, datetime

from sqlalchemy import delete, select

from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
from apps.funding.adapter.outbound.repositories.funding_program_repository import (
    SqlAlchemyFundingProgramRepository,
)
from apps.funding.app.ports.output.funding_program_port import FundingSearchGatewayPort
from apps.funding.app.use_cases.funding_program_interactor import (
    FundingProgramInteractor,
)
from apps.funding.domain.entities.funding_program_entity import FundingProgram
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_PREFIX = "test-funding-"


def _program(n: int, source_updated_at: datetime | None = None) -> FundingProgram:
    return FundingProgram(
        program_id=f"{_TEST_PREFIX}{n}",
        source="bizinfo",
        title=f"공고 {n}",
        org="기관",
        url=f"https://example.com/{_TEST_PREFIX}{n}",
        apply_period="2026-09-01 ~ 2026-09-30",
        deadline=date(2026, 9, 30),
        source_updated_at=source_updated_at or datetime(2026, 9, 1, 12, 0),
    )


class FakeGateway(FundingSearchGatewayPort):
    def __init__(self, programs: list[FundingProgram]) -> None:
        self._programs = programs

    def fetch_all(self) -> list[FundingProgram]:
        return self._programs


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(FundingProgramOrm).where(
                FundingProgramOrm.program_id.like(f"{_TEST_PREFIX}%")
            )
        )


def test_ingest_upsert_is_idempotent_and_dedups_batch():
    _cleanup()
    repository = SqlAlchemyFundingProgramRepository()
    # 배치 내 중복(동일 program_id 2회) 포함 3건 → 2건만 신규
    batch = [_program(1), _program(1), _program(2)]
    interactor = FundingProgramInteractor(repository=repository, gateway=FakeGateway(batch))

    assert interactor.ingest() == (2, 0)
    assert interactor.ingest() == (0, 0)  # 재실행 — 원천 갱신시점 동일이면 무변경

    # 원천 갱신(updtPnttm 변경 + 마감 연장) → 신규 0, 갱신 1
    changed = _program(1, source_updated_at=datetime(2026, 9, 5, 9, 0))
    changed.deadline = date(2026, 10, 31)
    changed.apply_period = "2026-09-01 ~ 2026-10-31"
    interactor2 = FundingProgramInteractor(
        repository=repository, gateway=FakeGateway([changed])
    )
    assert interactor2.ingest() == (0, 1)

    with session_scope() as session:
        stored = session.execute(
            select(FundingProgramOrm).where(
                FundingProgramOrm.program_id == f"{_TEST_PREFIX}1"
            )
        ).scalar_one()
        assert stored.deadline == date(2026, 10, 31)
    _cleanup()
