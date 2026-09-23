"""Driven Adapter — commerce BC 추정매출·점포에서 점포당 매출의 재료를 모은다.

`sales_amount`는 원천 컬럼명이 `당월_매출_금액`이지만 **분기 합**이다. 근거 —
① 원천 파일이 `기준_년분기_코드` 단위로만 온다(월 파일이 없다). ② 타당성: 역삼1동 카페(CS 3코드)
20254 = 353억 / 400점포 → ÷3 하면 2,944만/월·점포로 현실적이고, 월 값으로 읽으면 8,832만/월로
비현실적이다. ③ 서울 전체 점포당 값도 같은 자릿수다(v0.33.0 검증). 인터랙터가 ÷3을 맡는다.

업종에 CS 코드가 여러 개 붙는 경우(academy 4·cafe 3·hair_salon 3, v0.26.0 매핑 보정)는
매출 합 ÷ 점포 합 — 코드별로 나눠 평균하면 모집단이 쪼개진다.
"""

from sqlalchemy import and_, func, select

from apps.commerce.adapter.outbound.orms.region_commerce_sales_orm import RegionCommerceSalesOrm
from apps.commerce.adapter.outbound.orms.region_commerce_store_orm import RegionCommerceStoreOrm
from apps.finance.app.dtos.finance_dto import RevenueBasis
from apps.finance.app.ports.output.finance_port import RevenueFactsPort
from apps.master.adapter.outbound.orms.industry_source_code_orm import IndustrySourceCodeOrm
from core.matrix.grid_oracle_database_manager import session_scope

_SOURCE_SYSTEM = "seoul_commercial"


class RevenueFactsGateway(RevenueFactsPort):
    def latest_quarterly_sales_per_store(
        self, region_code: str, industry_id: str
    ) -> RevenueBasis | None:
        with session_scope() as session:
            codes = list(
                session.execute(
                    select(IndustrySourceCodeOrm.code).where(
                        IndustrySourceCodeOrm.industry_id == industry_id,
                        IndustrySourceCodeOrm.source_system == _SOURCE_SYSTEM,
                    )
                ).scalars()
            )
            if not codes:
                return None
            sales = RegionCommerceSalesOrm
            store = RegionCommerceStoreOrm
            row = session.execute(
                select(
                    sales.year_quarter,
                    func.sum(sales.sales_amount),
                    func.sum(store.store_count),
                )
                .join(
                    store,
                    and_(
                        store.adstrd_code == sales.adstrd_code,
                        store.service_industry_code == sales.service_industry_code,
                        store.year_quarter == sales.year_quarter,
                    ),
                )
                .where(
                    sales.region_code == region_code,
                    sales.service_industry_code.in_(codes),
                    sales.sales_amount.is_not(None),
                    store.store_count.is_not(None),
                )
                .group_by(sales.year_quarter)
                .order_by(sales.year_quarter.desc())
                .limit(1)
            ).one_or_none()
        if row is None:
            return None
        year_quarter, quarterly_sales, store_count = row
        if not store_count:
            return None
        return RevenueBasis(
            year_quarter=year_quarter,
            quarterly_sales=int(quarterly_sales),
            store_count=int(store_count),
            source_codes=sorted(codes),
        )
