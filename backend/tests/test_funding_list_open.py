"""GET /funding 목록 검증 — 미만료만, 마감 임박순(상시는 뒤), limit·에러 바디 계약."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import delete

from apps.funding.adapter.outbound.orm_mappers.funding_program_orm_mapper import to_orm
from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
from apps.funding.adapter.outbound.repositories.funding_program_repository import (
    SqlAlchemyFundingProgramRepository,
)
from apps.funding.domain.entities.funding_program_entity import FundingProgram
from apps.funding.dependencies.funding_program_dependencies import (
    get_funding_program_use_case,
)
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

_TEST_PREFIX = "test-fundlist-"


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


def test_list_open_orders_by_deadline_excludes_expired():
    _cleanup()
    with session_scope() as session:
        session.add(to_orm(_program(1, date(2026, 12, 1))))
        session.add(to_orm(_program(2, date(2026, 9, 10))))  # 가장 임박 → 첫 행
        session.add(to_orm(_program(3, None)))  # 상시 → 마지막
        session.add(to_orm(_program(4, date(2026, 9, 1), is_expired=True)))  # 만료 → 제외

    listed = [
        p
        for p in SqlAlchemyFundingProgramRepository().list_open(limit=100_000)  # 실DB 공존 행 무관하게 전수
        if p.program_id.startswith(_TEST_PREFIX)
    ]
    assert [p.program_id[-1] for p in listed] == ["2", "1", "3"]
    _cleanup()


def test_list_open_respects_limit():
    _cleanup()
    with session_scope() as session:
        for n in range(3):
            session.add(to_orm(_program(n, date(2001, 1, 1 + n))))  # 과거 마감 — 최상단 정렬 보장

    listed = SqlAlchemyFundingProgramRepository().list_open(limit=2)
    assert len(listed) == 2
    assert [p.program_id for p in listed] == [f"{_TEST_PREFIX}0", f"{_TEST_PREFIX}1"]
    _cleanup()


def test_router_invalid_limit_returns_error_body():
    client = TestClient(app)
    response = client.get("/funding", params={"limit": 0})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_LIMIT"
    assert body["error"]["message"]


def test_list_open_excludes_past_deadline_even_when_flag_is_stale():
    """플래그가 낡아도 마감 지난 공고는 목록에 없다.

    `is_expired`는 일 배치(`refresh_expirations`)가 갱신해 설계상 최대 하루 낡는다 —
    어제 마감한 공고가 다음 05:10까지 "모집 중"으로 남는 창이 있었다. 후보 필터
    (`domain/services/candidates.py`)와 같은 방어를 목록에도 둔다.
    """
    _cleanup()
    with session_scope() as session:
        # 마감은 지났는데 플래그가 아직 false — 배치가 돌기 전 창
        session.add(to_orm(_program(90, date(2020, 1, 1), is_expired=False)))
        session.add(to_orm(_program(91, date(2026, 12, 1))))

    listed = [
        dto
        for dto in get_funding_program_use_case().list_open(limit=100_000)
        if dto.program_id.startswith(_TEST_PREFIX)
    ]

    assert [dto.program_id[-2:] for dto in listed] == ["91"]
    _cleanup()
