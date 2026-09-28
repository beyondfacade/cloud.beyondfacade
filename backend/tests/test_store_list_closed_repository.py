"""폐업 점포 조회 리포지토리 — since 경계·좌표 없는 행 제외 (실 DB)."""

from datetime import date, datetime, timedelta

from sqlalchemy import delete, select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.store.adapter.outbound.repositories.store_repository import SqlAlchemyStoreRepository
from core.matrix.grid_oracle_database_manager import session_scope

_PREFIX = "test-closed-"
_TODAY = date(2099, 6, 30)


def _region_code() -> str:
    with session_scope() as session:
        return session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)).scalar_one()


def _store(n: int, region: str, close_date: date | None, lat: float | None = 37.5) -> StoreOrm:
    return StoreOrm(
        store_id=f"{_PREFIX}{n}", name=f"폐업시험{n}", industry_id="cafe", district_code=region[:5], region_code=region,
        subcategory_id=None, open_date=date(2095, 1, 1), close_date=close_date, status_code="03",
        status_name="폐업" if close_date else "영업", lat=lat, lng=None if lat is None else 127.0,
        road_address=None, jibun_address=None, source_updated_at=datetime(2099, 1, 1),
    )


def test_since_이후_폐업_좌표_보유_행만():
    region = _region_code()
    since = _TODAY - timedelta(days=730)
    rows = [
        _store(1, region, since),                      # 경계 포함
        _store(2, region, since - timedelta(days=1)),  # 경계 밖
        _store(3, region, _TODAY, lat=None),           # 좌표 없음 → 제외
        _store(4, region, None),                       # 영업 중 → 제외
    ]
    try:
        with session_scope() as session:
            session.add_all(rows)
        found = SqlAlchemyStoreRepository().list_closed_since(region, "cafe", since)
        assert [s.store_id for s in found if s.store_id.startswith(_PREFIX)] == [f"{_PREFIX}1"]
    finally:
        with session_scope() as session:
            session.execute(delete(StoreOrm).where(StoreOrm.store_id.like(f"{_PREFIX}%")))
