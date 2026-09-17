"""convenience 조회 리포지토리 검증 (실 DB) — 현행 판정 = 행정동 최신 관측일.

수집 단위가 행정동이므로 행정동별 max(last_seen_on)에 관측된 점포만 현행으로 본다 —
한 행정동 수집이 실패해도 그 동 점포가 이전 스냅샷 그대로 남는다.
"""

from datetime import date

from sqlalchemy import delete, select

from apps.convenience.adapter.outbound.orms.convenience_store_orm import ConvenienceStoreOrm
from apps.convenience.adapter.outbound.repositories.convenience_store_repository import (
    SqlAlchemyConvenienceStoreRepository,
)
from apps.convenience.domain.entities.convenience_store_entity import ConvenienceStore
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope

_PREFIX = "test-cvquery-"


def _region_code() -> str:
    with session_scope() as session:
        return session.execute(
            select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)
        ).scalar_one()


def _store(n: int, region_code: str) -> ConvenienceStore:
    return ConvenienceStore(
        store_id=f"{_PREFIX}{n}", name=f"시험편의점{n}", branch_name=None, brand="CU",
        region_code=region_code, lat=37.5, lng=127.0, road_address=None, jibun_address=None,
        source_stdr_ym="202606",
    )


def _cleanup():
    with session_scope() as session:
        session.execute(
            delete(ConvenienceStoreOrm).where(ConvenienceStoreOrm.store_id.like(f"{_PREFIX}%"))
        )


def test_list_current_returns_only_latest_seen_in_region():
    _cleanup()
    region_code = _region_code()
    repository = SqlAlchemyConvenienceStoreRepository()
    # 실적재 최신 관측일보다 뒤 — 시험 행정동의 최신 관측일을 시험 행이 결정하게 한다
    repository.upsert([_store(1, region_code), _store(2, region_code)], date(2099, 1, 1))
    repository.upsert([_store(1, region_code)], date(2099, 1, 8))

    stores = repository.list_current(region_code)
    assert [s.store_id for s in stores] == [f"{_PREFIX}1"]  # 소실된 2번·이전 스냅샷 실적재 행 제외
    _cleanup()
