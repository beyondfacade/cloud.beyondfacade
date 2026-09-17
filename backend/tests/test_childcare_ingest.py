"""childcare snapshot ingest 검증 — 시설 멱등 업서트 + 기준일별 현황 이력 (실 DB).

convenience 전례의 first/last_seen 관측 패턴을 따르되, 정원·현원·대기는 시점마다 변하므로
childcare_center_stat에 원천 기준일(datastdrdt)별 행으로 쌓는다 (덮어쓰면 가동률 추이 소실).
"""

from datetime import date

from sqlalchemy import delete, select, update

from apps.childcare.adapter.outbound.orms.childcare_center_orm import ChildcareCenterOrm
from apps.childcare.adapter.outbound.orms.childcare_center_stat_orm import (
    ChildcareCenterStatOrm,
)
from apps.childcare.adapter.outbound.repositories.childcare_center_repository import (
    SqlAlchemyChildcareCenterRepository,
)
from apps.childcare.app.ports.output.childcare_center_port import ChildcareGatewayPort
from apps.childcare.app.use_cases.childcare_center_interactor import (
    ChildcareSnapshotInteractor,
)
from apps.childcare.domain.entities.childcare_center_entity import ChildcareCenter
from apps.childcare.domain.entities.childcare_center_stat_entity import ChildcareCenterStat
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_PREFIX = "test-childcare-"
_DISTRICT = "11110"  # 종로구 (seed_master 시드)


def _center(n: int, base_date: date, child_count: int = 25, name: str | None = None) -> ChildcareCenter:
    return ChildcareCenter(
        center_id=f"{_TEST_PREFIX}{n}",
        name=name or f"시험어린이집{n}",
        type_name="국공립",
        status_name="정상",
        district_code=_DISTRICT,
        address="서울특별시 종로구 시험로 1",
        zipcode=None,
        tel=None,
        lat=37.58,
        lng=126.98,
        approved_on=date(1995, 6, 23),
        paused_from=None,
        paused_until=None,
        abolished_on=None,
        stat=ChildcareCenterStat(
            base_date=base_date,
            capacity=39,
            child_count=child_count,
            waiting_count=None,
            class_count=7,
            staff_count=10,
        ),
    )


class FakeGateway(ChildcareGatewayPort):
    def __init__(self, centers: list[ChildcareCenter]) -> None:
        self._centers = centers

    def fetch_centers(self, district_code: str) -> list[ChildcareCenter]:
        return self._centers


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(ChildcareCenterStatOrm).where(
                ChildcareCenterStatOrm.center_id.like(f"{_TEST_PREFIX}%")
            )
        )
        session.execute(
            delete(ChildcareCenterOrm).where(ChildcareCenterOrm.center_id.like(f"{_TEST_PREFIX}%"))
        )


def _centers() -> dict[str, tuple]:
    with session_scope() as session:
        rows = session.execute(
            select(ChildcareCenterOrm).where(ChildcareCenterOrm.center_id.like(f"{_TEST_PREFIX}%"))
        ).scalars()
        return {r.center_id: (r.first_seen_on, r.last_seen_on, r.name, r.region_code) for r in rows}


def _stats(center_id: str) -> list[tuple]:
    with session_scope() as session:
        rows = session.execute(
            select(ChildcareCenterStatOrm)
            .where(ChildcareCenterStatOrm.center_id == center_id)
            .order_by(ChildcareCenterStatOrm.base_date)
        ).scalars()
        return [(r.base_date, r.child_count) for r in rows]


def _ingest(centers: list[ChildcareCenter], observed_on: date) -> int:
    interactor = ChildcareSnapshotInteractor(
        repository=SqlAlchemyChildcareCenterRepository(), gateway=FakeGateway(centers)
    )
    return interactor.ingest(_DISTRICT, observed_on)


def test_first_load_sets_seen_dates_and_stat_row():
    _cleanup()
    processed = _ingest([_center(1, date(2026, 9, 17))], date(2026, 9, 17))
    assert processed == 1
    first_seen, last_seen, _, _ = _centers()[f"{_TEST_PREFIX}1"]
    assert (first_seen, last_seen) == (date(2026, 9, 17), date(2026, 9, 17))
    assert _stats(f"{_TEST_PREFIX}1") == [(date(2026, 9, 17), 25)]
    _cleanup()


def test_same_base_date_reingest_is_idempotent():
    _cleanup()
    _ingest([_center(1, date(2026, 9, 17))], date(2026, 9, 17))
    _ingest([_center(1, date(2026, 9, 17), child_count=26, name="개명어린이집")], date(2026, 9, 17))
    assert _stats(f"{_TEST_PREFIX}1") == [(date(2026, 9, 17), 26)]  # 행 중복 없이 값 갱신
    assert _centers()[f"{_TEST_PREFIX}1"][2] == "개명어린이집"
    _cleanup()


def test_new_base_date_appends_stat_history_and_keeps_first_seen():
    _cleanup()
    _ingest([_center(1, date(2026, 9, 17))], date(2026, 9, 17))
    _ingest([_center(1, date(2026, 9, 24), child_count=30)], date(2026, 9, 24))
    assert _stats(f"{_TEST_PREFIX}1") == [(date(2026, 9, 17), 25), (date(2026, 9, 24), 30)]
    assert _centers()[f"{_TEST_PREFIX}1"][:2] == (date(2026, 9, 17), date(2026, 9, 24))
    _cleanup()


def test_missing_center_keeps_stale_last_seen():
    """원천은 폐지 시설을 응답에서 뺀다(정상·재개·휴지·공란만 실측) — 소실 = last_seen_on 정지로만 기록."""
    _cleanup()
    _ingest([_center(1, date(2026, 9, 17)), _center(2, date(2026, 9, 17))], date(2026, 9, 17))
    _ingest([_center(1, date(2026, 9, 24))], date(2026, 9, 24))
    rows = _centers()
    assert rows[f"{_TEST_PREFIX}1"][:2] == (date(2026, 9, 17), date(2026, 9, 24))
    assert rows[f"{_TEST_PREFIX}2"][:2] == (date(2026, 9, 17), date(2026, 9, 17))
    _cleanup()


def test_blank_status_center_is_stored():
    _cleanup()
    center = _center(1, date(2026, 9, 17))
    processed = _ingest([ChildcareCenter(**{**center.__dict__, "status_name": None})], date(2026, 9, 17))
    assert processed == 1
    _cleanup()


def test_reingest_preserves_assigned_region_code():
    """region_code는 공간조인이 기입한다 — 재수집 업서트가 NULL로 되돌리면 안 된다."""
    _cleanup()
    _ingest([_center(1, date(2026, 9, 17))], date(2026, 9, 17))
    with session_scope() as session:
        region_code = session.execute(
            select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)
        ).scalar_one()
        session.execute(
            update(ChildcareCenterOrm)
            .where(ChildcareCenterOrm.center_id == f"{_TEST_PREFIX}1")
            .values(region_code=region_code)
        )
    _ingest([_center(1, date(2026, 9, 24))], date(2026, 9, 24))
    assert _centers()[f"{_TEST_PREFIX}1"][3] == region_code
    _cleanup()
