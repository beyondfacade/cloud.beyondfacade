"""서울 업종별 점포당 매출 중앙값 사전 계산 — 집계·멱등·재무 게이트웨이 읽기.

11차 부하 테스트에서 재무 프리필이 요청마다 다시 계산하던 이 중앙값이 DB 시간의 대부분이었다
(설계 docs/superpowers/specs/2026-10-23-seoul-sales-median-design.md). 값은 업종×분기에만 달려 있어 미리 계산해 둔다.
"""

import pytest
from sqlalchemy import delete, select

from apps.commerce.adapter.outbound.orms.region_commerce_sales_orm import RegionCommerceSalesOrm
from apps.commerce.adapter.outbound.orms.region_commerce_store_orm import RegionCommerceStoreOrm
from apps.finance.adapter.outbound.gateways.revenue_facts_gateway import RevenueFactsGateway
from apps.master.adapter.outbound.orms.industry_source_code_orm import IndustrySourceCodeOrm
from apps.metric.adapter.outbound.orms.industry_sales_median_orm import IndustrySalesMedianOrm
from apps.metric.dependencies.industry_sales_median_dependencies import (
    get_industry_sales_median_use_case,
)
from core.matrix.grid_oracle_database_manager import session_scope

_QUARTER = "19991"  # 원천에 없는 분기 — 다른 데이터와 섞이지 않게
_EXTRA_PUB_CODE = "TS9000P1"  # 주점에 임시로 붙이는 두 번째 원천 코드
_R1, _R2, _R3, _R4, _R5 = "1111051500", "1135056000", "1144055500", "1162052500", "1168051000"

# (원천 행정동, 원천 업종 코드, 행정동, 분기 매출, 점포 수)
_ROWS = [
    # 한식(코드 1개): 동별 점포당 100 · 200 · 300 → 중앙값 200
    ("99999991", "CS100001", _R1, 300, 3),
    ("99999992", "CS100001", _R2, 1000, 5),
    ("99999993", "CS100001", _R3, 900, 3),
    ("99999994", "CS100001", _R4, 500, 0),  # 점포 0인 동은 빠진다
    ("99999995", "CS100001", _R5, None, 4),  # 매출 없는 행은 빠진다
    # 주점(코드 2개): 동 안에서 코드를 합쳐 나눈다 — R1 (100+300)/2=200, R2 (200+400)/2=300 → 중앙값 250
    ("99999991", "CS100009", _R1, 100, 1),
    ("99999991", _EXTRA_PUB_CODE, _R1, 300, 1),
    ("99999992", "CS100009", _R2, 200, 1),
    ("99999992", _EXTRA_PUB_CODE, _R2, 400, 1),
]


def _cleanup() -> None:
    with session_scope() as session:
        session.execute(delete(IndustrySalesMedianOrm).where(IndustrySalesMedianOrm.year_quarter == _QUARTER))
        session.execute(delete(RegionCommerceSalesOrm).where(RegionCommerceSalesOrm.year_quarter == _QUARTER))
        session.execute(delete(RegionCommerceStoreOrm).where(RegionCommerceStoreOrm.year_quarter == _QUARTER))
        session.execute(delete(IndustrySourceCodeOrm).where(IndustrySourceCodeOrm.code == _EXTRA_PUB_CODE))


@pytest.fixture
def commerce_rows():
    _cleanup()
    with session_scope() as session:
        session.add(IndustrySourceCodeOrm(industry_id="pub", source_system="seoul_commercial", code=_EXTRA_PUB_CODE))
        for adstrd, code, region, sales, stores in _ROWS:
            key = {"adstrd_code": adstrd, "service_industry_code": code, "year_quarter": _QUARTER, "region_code": region}
            session.add(RegionCommerceSalesOrm(**key, sales_amount=sales))
            session.add(RegionCommerceStoreOrm(**key, store_count=stores))
    yield
    _cleanup()


def _stored(industry_id: str) -> IndustrySalesMedianOrm | None:
    with session_scope() as session:
        orm = session.get(IndustrySalesMedianOrm, (industry_id, _QUARTER))
        if orm is not None:
            session.expunge(orm)
        return orm


def test_업종마다_동별_점포당_매출의_서울_중앙값을_분기별로_저장한다(commerce_rows):
    get_industry_sales_median_use_case().build()

    korean = _stored("korean_food")
    assert (korean.median_quarterly_sales_per_store, korean.region_count) == (200, 3)
    pub = _stored("pub")
    assert (pub.median_quarterly_sales_per_store, pub.region_count) == (250, 2)


def test_다시_계산해도_행이_늘지_않고_값이_같다(commerce_rows):
    use_case = get_industry_sales_median_use_case()
    use_case.build()
    use_case.build()

    with session_scope() as session:
        rows = session.execute(
            select(IndustrySalesMedianOrm.industry_id).where(IndustrySalesMedianOrm.year_quarter == _QUARTER)
        ).scalars().all()
    assert sorted(rows) == ["korean_food", "pub"]
    assert _stored("korean_food").median_quarterly_sales_per_store == 200


def test_재무_프리필은_저장된_서울_중앙값을_읽는다(commerce_rows):
    get_industry_sales_median_use_case().build()

    basis = RevenueFactsGateway().latest_quarterly_sales_per_store(_R1, "korean_food")

    assert basis.year_quarter == _QUARTER
    assert basis.seoul_median_quarterly_sales_per_store == 200.0


def test_저장된_중앙값이_없으면_서울_중앙값만_비운다(commerce_rows):
    basis = RevenueFactsGateway().latest_quarterly_sales_per_store(_R1, "korean_food")

    assert (basis.quarterly_sales, basis.store_count) == (300, 3)
    assert basis.seoul_median_quarterly_sales_per_store is None
