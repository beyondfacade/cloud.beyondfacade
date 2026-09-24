"""store 연도별 집계 게이트웨이 검증 (실 DB) — 폐업 이력이 없는 원천은 폐업수를 0이 아니라 None으로 준다.

서울 학원 API는 폐원일자를 주지 않아 academy의 close_date가 전부 NULL이다. 그 0건을 폐업 0으로 세면
폐업률 0.0이 값처럼 보인다(STATUS §4-3). 카페처럼 개폐업 이력이 있는 원천은 그대로 센다.
"""

from datetime import date, datetime

from sqlalchemy import delete, select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.metric.adapter.outbound.gateways.store_stats_gateway import StoreStatsGateway
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from core.matrix.grid_oracle_database_manager import session_scope

_PREFIX = "test-storestats-"
_YEAR = 2098  # 실적재보다 뒤 — 시험 행만 이 연도에 잡힌다


def _region_code() -> str:
    with session_scope() as session:
        return session.execute(
            select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)
        ).scalar_one()


def _store(n: int, industry_id: str, region_code: str, close_date: date | None) -> StoreOrm:
    return StoreOrm(
        store_id=f"{_PREFIX}{industry_id}-{n}", name=f"집계시험{n}", industry_id=industry_id,
        district_code=region_code[:5], region_code=region_code, subcategory_id=None,
        open_date=date(_YEAR, 3, 1), close_date=close_date, status_code="01", status_name="영업",
        lat=None, lng=None, road_address=None, jibun_address=None,
        source_updated_at=datetime(_YEAR, 3, 1),
    )


def test_yearly_stats_reports_none_close_count_for_source_without_closure_history():
    region_code = _region_code()
    try:
        with session_scope() as session:
            session.add_all([
                _store(1, "academy", region_code, None),
                _store(2, "academy", region_code, None),
                _store(3, "cafe", region_code, None),
                _store(4, "cafe", region_code, date(_YEAR, 9, 1)),
            ])

        by_industry = {
            s.industry_id: s
            for s in StoreStatsGateway().yearly_stats([_YEAR])
            if s.region_code == region_code
        }

        academy, cafe = by_industry["academy"], by_industry["cafe"]
        assert (academy.store_count, academy.open_count) == (2, 2)
        assert academy.close_count is None  # 폐업 0건이 아니라 "모른다"
        assert (cafe.store_count, cafe.open_count, cafe.close_count) == (1, 2, 1)
    finally:
        with session_scope() as session:
            session.execute(delete(StoreOrm).where(StoreOrm.store_id.like(f"{_PREFIX}%")))
