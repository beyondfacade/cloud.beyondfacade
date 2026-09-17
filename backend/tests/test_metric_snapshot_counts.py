"""스냅샷 원천 점포수 게이트웨이 검증 (실 DB) — 조회 API와 같은 현행 판정으로 행정동별 집계.

어린이집 = 자치구 최신 관측일에 관측된 시설, 편의점 = 행정동 최신 관측일에 관측된 점포.
연도 = 최신 관측일의 연도. region_code 미기입 시설은 집계 대상이 아니다.
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
from apps.childcare.domain.entities.childcare_center_entity import ChildcareCenter
from apps.childcare.domain.entities.childcare_center_stat_entity import ChildcareCenterStat
from apps.convenience.adapter.outbound.orms.convenience_store_orm import ConvenienceStoreOrm
from apps.convenience.adapter.outbound.repositories.convenience_store_repository import (
    SqlAlchemyConvenienceStoreRepository,
)
from apps.convenience.domain.entities.convenience_store_entity import ConvenienceStore
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.metric.adapter.outbound.gateways.snapshot_store_count_gateways import (
    ChildcareStoreCountGateway,
    ConvenienceStoreCountGateway,
)
from core.matrix.grid_oracle_database_manager import session_scope

_PREFIX = "test-snapcount-"
_OLD, _NEW = date(2099, 1, 1), date(2099, 1, 8)  # 실적재보다 뒤 — 시험 행이 최신 관측일을 결정


def _region_code() -> str:
    with session_scope() as session:
        return session.execute(
            select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)
        ).scalar_one()


def _center(n: int, region_code: str, base_date: date) -> ChildcareCenter:
    return ChildcareCenter(
        center_id=f"{_PREFIX}{n}", name=f"집계시험{n}", type_name="국공립", status_name="정상",
        district_code=region_code[:5], address="시험로 1", zipcode=None, tel=None,
        lat=37.5, lng=127.0, approved_on=None, paused_from=None, paused_until=None,
        abolished_on=None,
        stat=ChildcareCenterStat(base_date=base_date, capacity=10, child_count=5,
                                 waiting_count=None, class_count=1, staff_count=2),
    )


def _store(n: int, region_code: str) -> ConvenienceStore:
    return ConvenienceStore(
        store_id=f"{_PREFIX}{n}", name=f"집계시험{n}", branch_name=None, brand=None,
        region_code=region_code, lat=37.5, lng=127.0, road_address=None, jibun_address=None,
        source_stdr_ym="209901",
    )


def _cleanup():
    with session_scope() as session:
        session.execute(delete(ChildcareCenterStatOrm).where(ChildcareCenterStatOrm.center_id.like(f"{_PREFIX}%")))
        session.execute(delete(ChildcareCenterOrm).where(ChildcareCenterOrm.center_id.like(f"{_PREFIX}%")))
        session.execute(delete(ConvenienceStoreOrm).where(ConvenienceStoreOrm.store_id.like(f"{_PREFIX}%")))


def _count_for(counts, region_code: str, industry_id: str):
    return [(c.year, c.store_count) for c in counts
            if c.region_code == region_code and c.industry_id == industry_id]


def test_childcare_counts_operating_centers_with_region():
    _cleanup()
    region_code = _region_code()
    repository = SqlAlchemyChildcareCenterRepository()
    # 1·2·3 최초 관측 → 다음 스냅샷에서 3 소실, 4는 region 미기입
    repository.upsert([_center(n, region_code, _OLD) for n in (1, 2, 3)], _OLD)
    repository.upsert([_center(n, region_code, _NEW) for n in (1, 2, 4)], _NEW)
    with session_scope() as session:
        session.execute(
            update(ChildcareCenterOrm)
            .where(ChildcareCenterOrm.center_id.in_([f"{_PREFIX}{n}" for n in (1, 2, 3)]))
            .values(region_code=region_code)
        )

    counts = ChildcareStoreCountGateway().current_counts()
    assert _count_for(counts, region_code, "childcare") == [(2099, 2)]
    _cleanup()


def test_convenience_counts_latest_seen_stores_in_region():
    _cleanup()
    region_code = _region_code()
    repository = SqlAlchemyConvenienceStoreRepository()
    repository.upsert([_store(n, region_code) for n in (1, 2, 3)], _OLD)
    repository.upsert([_store(n, region_code) for n in (1, 2)], _NEW)

    counts = ConvenienceStoreCountGateway().current_counts()
    assert _count_for(counts, region_code, "convenience_store") == [(2099, 2)]
    _cleanup()
