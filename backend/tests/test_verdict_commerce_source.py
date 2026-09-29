"""상권분석 집계 원천 — 4분기 창·동 합산·점포수 상한·재고 결과 (업종 특화 신호 설계서 §7, 실 DB)."""

from datetime import date

from sqlalchemy import delete, select

from apps.commerce.adapter.outbound.orms.region_commerce_store_orm import RegionCommerceStoreOrm
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.verdict.adapter.outbound.gateways.commerce_aggregate_gateway import CommerceAggregateSignalData
from core.matrix.grid_oracle_database_manager import session_scope

_ADSTRD = ("T9700001", "T9700002")
_CODE = "CS200033"  # real_estate ↔ seoul_commercial (마이그레이션 c7a4f2e19b35 시드)


def _region() -> str:
    with session_scope() as session:
        return session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code).limit(1)).scalar_one()


def _row(adstrd, region, quarter, store, opened=0, closed=0):
    return RegionCommerceStoreOrm(
        adstrd_code=adstrd, service_industry_code=_CODE, year_quarter=quarter, region_code=region,
        store_count=store, similar_industry_store_count=None, open_rate=None, open_store_count=opened,
        close_rate=None, close_store_count=closed, franchise_store_count=None,
    )


def test_집계_원천은_최근_4분기_폐업과_4분기_전_점포수를_동별로_합한다():
    region = _region()
    rows = [
        _row(_ADSTRD[0], region, "20973", 100, opened=3, closed=5),
        _row(_ADSTRD[0], region, "20974", 102, opened=6, closed=4),
        _row(_ADSTRD[0], region, "20981", 101, opened=1, closed=3),
        _row(_ADSTRD[0], region, "20982", 99, opened=2, closed=2),
        _row(_ADSTRD[0], region, "20983", 90, opened=0, closed=6),
        _row(_ADSTRD[0], region, "20984", 80, opened=0, closed=9),  # 기준 분기 뒤 — 창 밖
        _row(_ADSTRD[1], region, "20973", 10),  # 같은 동의 두 번째 상권코드
        _row(_ADSTRD[1], region, "20983", 10, closed=1),
    ]
    try:
        with session_scope() as session:
            session.add_all(rows)
        data = CommerceAggregateSignalData(("real_estate",))
        # today 2098-12-31 → 직전 분기 20983 → 창 (20973, 20983]
        stat = next(s for s in data.signal_stats(date(2098, 12, 31)) if s.region_code == region)
        assert stat.industry_id == "real_estate"
        assert stat.start_store_count == 110  # 20973: 100 + 10
        assert stat.closed_12m == 4 + 3 + 2 + 6 + 1
        assert stat.opened_12m == 6 + 1 + 2 + 0
        assert (stat.cohort_size, stat.closed_3y_count, stat.closed_3y_median_months) == (0, 0, None)
        count = lambda quarter_max: next(  # noqa: E731
            c.store_count for c in data.store_counts(None, quarter_max) if c.region_code == region
        )
        assert count(None) == 80  # 최신 20984
        assert count("20982") == 99
        outcome = next(o for o in data.entrant_outcomes(date(2097, 9, 30), 365, 365) if o.region_code == region)
        assert (outcome.opened, outcome.closed_within) == (110, 4 + 3 + 2 + 6 + 1)  # 노출 20973, 폐업 20974~20983
    finally:
        with session_scope() as session:
            session.execute(delete(RegionCommerceStoreOrm).where(RegionCommerceStoreOrm.adstrd_code.in_(_ADSTRD)))
