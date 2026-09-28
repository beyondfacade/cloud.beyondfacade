"""판정 게이트웨이 — store 집계 SQL(12개월·코호트·중위개월 경계)과 업종 카탈로그 제외 (실 DB)."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.verdict.adapter.outbound.gateways.industry_catalog_gateway import IndustryCatalogGateway
from apps.verdict.adapter.outbound.gateways.region_context_gateway import RegionContextGateway
from apps.verdict.adapter.outbound.gateways.store_signal_stats_gateway import StoreSignalStatsGateway
from apps.verdict.domain.entities.region_industry_verdict_entity import EXCLUDED_INDUSTRIES
from core.matrix.grid_oracle_database_manager import session_scope

_PREFIX = "test-verdictstats-"
_TODAY = date(2099, 6, 30)  # 실적재보다 뒤 — 시험 행만 이 창에 잡힌다
_INDUSTRY = "korean_food"


def _region_code() -> str:
    with session_scope() as session:
        return session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)).scalar_one()


def _store(n: int, region: str, open_date: date, close_date: date | None) -> StoreOrm:
    return StoreOrm(
        store_id=f"{_PREFIX}{n}", name=f"판정시험{n}", industry_id=_INDUSTRY, district_code=region[:5],
        region_code=region, subcategory_id=None, open_date=open_date, close_date=close_date,
        status_code="01", status_name="영업" if close_date is None else "폐업",
        lat=None, lng=None, road_address=None, jibun_address=None, source_updated_at=datetime(2099, 1, 1),
    )


def test_store_집계_12개월_코호트_중위개월():
    region = _region_code()
    d = lambda days: _TODAY - timedelta(days=days)  # noqa: E731
    # 개업/폐업일은 전부 today(2099-06-30) 기준 N일 전. 창: 12개월 = 365일, 코호트 = [1460, 1095)일 전 개업, 3년 = 1095일
    rows = [
        _store(1, region, d(800), None),      # 12개월 전 영업 → start. 폐업 없음
        _store(2, region, d(800), d(100)),    # start · closed_12m · closed_3y (영업 700일)
        _store(3, region, d(100), None),      # opened_12m
        _store(4, region, d(1195), None),     # 코호트 · 생존 · start
        _store(5, region, d(1195), d(795)),   # 코호트 · 400일 만에 폐업 → 미생존 · closed_3y (start 아님: 12개월 전 이미 폐업)
        _store(6, region, d(1195), d(95)),    # 코호트 · 1100일 뒤 폐업 → 생존(≥1095) · start · closed_12m · closed_3y
        _store(7, region, d(2000), d(200)),   # start · closed_12m · closed_3y (영업 1800일)
        _store(8, region, d(100), d(200)),    # 오염 행: 폐업일<개업일(영업일수 -100일) — opened_12m·closed_12m엔 잡히되 closed_3y·중앙값에서는 빠져야 함
    ]
    try:
        with session_scope() as session:
            session.add_all(rows)
        stat = next(s for s in StoreSignalStatsGateway().signal_stats(_TODAY)
                    if s.region_code == region and s.industry_id == _INDUSTRY)
        # 실적재 행은 2099 창에 안 잡힌다(개업·폐업일이 전부 과거) — 시험 행만 센다
        assert stat.start_store_count == 5  # 1, 2, 4, 6, 7 (5는 12개월 전 이미 폐업, 3은 그 뒤 개업, 8은 12개월 전 미개업)
        assert stat.opened_12m == 2  # 3, 8
        assert stat.closed_12m == 4  # 2, 6, 7, 8
        assert stat.cohort_size == 3 and stat.cohort_survived == 2  # 4·5·6 중 4·6
        # 8은 close_date가 창 안이지만 days_open<0(폐업일<개업일)이라 제외 — 오염 행이 껴도 4·중앙값 그대로
        assert stat.closed_3y_count == 4  # 2, 5, 6, 7
        # 영업일수 700·400·1100·1800 → 중위 900일 ≈ 29.6개월
        assert stat.closed_3y_median_months == pytest.approx(900 / 30.4375, rel=1e-3)
    finally:
        with session_scope() as session:
            session.execute(delete(StoreOrm).where(StoreOrm.store_id.like(f"{_PREFIX}%")))


def test_동_맥락은_전_행정동을_한_행씩_준다():
    contexts = RegionContextGateway().latest_contexts()
    codes = [c.region_code for c in contexts]
    assert len(codes) == len(set(codes)) >= 400
    counts = RegionContextGateway().latest_store_counts()
    assert all(c.store_count >= 0 for c in counts)


def test_판정_대상_업종은_제외_5종을_뺀_13종():
    judged = IndustryCatalogGateway().judged_industries()
    ids = {i.industry_id for i in judged}
    assert len(ids) == 13
    assert ids.isdisjoint(EXCLUDED_INDUSTRIES)
    assert next(i.name for i in judged if i.industry_id == "korean_food") == "한식"
