"""childcare 조회 리포지토리 검증 (실 DB) — 운영 판정·최신 현황 선택·좌표 필터.

운영 중 = 자치구 최신 관측일(max last_seen_on)에 관측된 시설 — 한 구의 수집이 실패해도
그 구 시설이 지도에서 사라지지 않도록 전역이 아닌 자치구 단위로 판정한다.
"""

from dataclasses import replace
from datetime import date

from sqlalchemy import delete, select, update

from apps.childcare.adapter.outbound.orms.childcare_center_orm import ChildcareCenterOrm
from apps.childcare.adapter.outbound.orms.childcare_center_stat_orm import (
    ChildcareCenterStatOrm,
)
from apps.childcare.adapter.outbound.repositories.childcare_center_repository import (
    SqlAlchemyChildcareCenterRepository,
)
from apps.childcare.adapter.outbound.repositories.childcare_center_stat_repository import (
    SqlAlchemyChildcareCenterStatRepository,
)
from apps.childcare.domain.entities.childcare_center_entity import ChildcareCenter
from apps.childcare.domain.entities.childcare_center_stat_entity import ChildcareCenterStat
from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope

_PREFIX = "test-ccquery-"
# 실적재 최신 관측일보다 뒤 — 시험 자치구의 최신 관측일을 시험 행이 결정하게 한다
_OLD, _NEW = date(2099, 1, 1), date(2099, 1, 8)


def _test_district() -> tuple[str, str]:
    """시험용 (district_code, region_code) — 실적재가 없는 구가 없으므로 첫 region을 쓰고 cleanup으로 원복."""
    with session_scope() as session:
        region_code = session.execute(
            select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)
        ).scalar_one()
        district_code = session.execute(
            select(DistrictOrm.district_code).where(
                DistrictOrm.district_code == region_code[:5]
            )
        ).scalar_one()
    return district_code, region_code


def _center(n: int, district_code: str, *, lat: float | None = 37.58, base_date: date = _NEW,
            child_count: int = 25) -> ChildcareCenter:
    return ChildcareCenter(
        center_id=f"{_PREFIX}{n}",
        name=f"조회시험{n}",
        type_name="국공립",
        status_name="정상",
        district_code=district_code,
        address="서울특별시 시험로 1",
        zipcode=None,
        tel=None,
        lat=lat,
        lng=None if lat is None else 126.98,
        approved_on=None,
        paused_from=None,
        paused_until=None,
        abolished_on=None,
        stat=ChildcareCenterStat(
            base_date=base_date, capacity=40, child_count=child_count,
            waiting_count=None, class_count=3, staff_count=5,
        ),
    )


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(ChildcareCenterStatOrm).where(ChildcareCenterStatOrm.center_id.like(f"{_PREFIX}%"))
        )
        session.execute(
            delete(ChildcareCenterOrm).where(ChildcareCenterOrm.center_id.like(f"{_PREFIX}%"))
        )


def _seed() -> str:
    """c1: 최신 관측 + 현황 2기준일, c2: 소실(이전 관측만), c3: 최신 관측·좌표 없음."""
    district_code, region_code = _test_district()
    writer = SqlAlchemyChildcareCenterRepository()
    c1, c2, c3 = (_center(1, district_code), _center(2, district_code),
                  _center(3, district_code, lat=None))
    writer.upsert([replace(c1, stat=replace(c1.stat, base_date=_OLD, child_count=10)), c2, c3], _OLD)
    writer.upsert([c1, c3], _NEW)
    with session_scope() as session:
        session.execute(
            update(ChildcareCenterOrm)
            .where(ChildcareCenterOrm.center_id.like(f"{_PREFIX}%"))
            .values(region_code=region_code)
        )
    return region_code


def test_list_operating_returns_latest_seen_with_coords_and_latest_stat():
    _cleanup()
    region_code = _seed()
    centers = [c for c in SqlAlchemyChildcareCenterRepository().list_operating(region_code)
               if c.center_id.startswith(_PREFIX)]
    assert [c.center_id for c in centers] == [f"{_PREFIX}1"]
    assert (centers[0].stat.base_date, centers[0].stat.child_count) == (_NEW, 25)
    _cleanup()


def test_list_latest_stats_includes_operating_centers_without_coords():
    _cleanup()
    region_code = _seed()
    stats = SqlAlchemyChildcareCenterStatRepository().list_latest(region_code)
    # 시험 구의 최신 관측일이 2099-01-08이 되어 실적재 행은 소실로 판정 — c1·c3의 최신 현황만 남는다
    assert sorted((s.base_date, s.child_count) for s in stats) == [(_NEW, 25), (_NEW, 25)]
    _cleanup()
