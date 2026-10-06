"""Driven Adapter — 백테스트 전용 후보 신호 재료 DB 읽기 (운영 판정 배치는 쓰지 않는다). cross-BC 접근은 이 파일 안에서만.
수요: region_population_quarter 상주·직장 총계 + region_footfall_quarter 유동 총계(분기 합 ÷ 분기 일수 = 일평균), 2021Q1~.
매출: region_commerce_sales 추정매출 합 ÷ region_commerce_store 점포수 합 (industry_source_code 'seoul_commercial' 매핑), 2021Q1~.
`backtest_multi` CLI가 호출한다."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select

from apps.commerce.adapter.outbound.orms.region_commerce_sales_orm import RegionCommerceSalesOrm
from apps.commerce.adapter.outbound.orms.region_commerce_store_orm import RegionCommerceStoreOrm
from apps.master.adapter.outbound.orms.industry_source_code_orm import IndustrySourceCodeOrm
from apps.neighborhood.adapter.outbound.orms.region_footfall_quarter_orm import RegionFootfallQuarterOrm
from apps.neighborhood.adapter.outbound.orms.region_population_quarter_orm import RegionPopulationQuarterOrm
from core.matrix.grid_oracle_database_manager import session_scope

_SOURCE_SYSTEM = "seoul_commercial"


@dataclass(frozen=True)
class DemandData:
    residents: dict[str, int]
    workers: dict[str, int]  # 직장인구 없는 동은 키가 없다 (0으로 채우지 않는다)
    footfall_daily: dict[str, int]


def _days_in_quarter(year_quarter: str) -> int:
    year, quarter = int(year_quarter[:4]), int(year_quarter[4])
    start = date(year, 3 * quarter - 2, 1)
    end = date(year + 1, 1, 1) if quarter == 4 else date(year, 3 * quarter + 1, 1)
    return (end - start).days


class CandidateSignalGateway:
    def demand(self, year_quarter: str) -> DemandData:
        P, F = RegionPopulationQuarterOrm, RegionFootfallQuarterOrm
        with session_scope() as session:
            population = session.execute(
                select(P.population_type, P.region_code, func.sum(P.headcount))
                .where(P.year_quarter == year_quarter, P.dim_type == "total", P.region_code.is_not(None))
                .group_by(P.population_type, P.region_code)
            ).all()
            footfall = session.execute(
                select(F.region_code, func.sum(F.headcount))
                .where(F.year_quarter == year_quarter, F.dim_type == "total", F.region_code.is_not(None))
                .group_by(F.region_code)
            ).all()
        by_type: dict[str, dict[str, int]] = {"resident": {}, "worker": {}}
        for population_type, region, headcount in population:
            by_type[population_type][region] = int(headcount)
        days = _days_in_quarter(year_quarter)
        return DemandData(
            residents=by_type["resident"], workers=by_type["worker"],
            footfall_daily={region: round(int(total) / days) for region, total in footfall},
        )

    def sales(self, year_quarter: str, industry_ids: Iterable[str]) -> dict[tuple[str, str], tuple[int, int]]:
        """(동, 업종) → (추정매출 합, 점포수 합). 업종에 서비스업종 코드가 여럿이면 동 단위로 합한다."""
        Sa, St, M = RegionCommerceSalesOrm, RegionCommerceStoreOrm, IndustrySourceCodeOrm
        with session_scope() as session:
            industry_of = dict(session.execute(
                select(M.code, M.industry_id).where(M.source_system == _SOURCE_SYSTEM, M.industry_id.in_(list(industry_ids)))
            ).all())
            amounts = session.execute(
                select(Sa.region_code, Sa.service_industry_code, func.coalesce(func.sum(Sa.sales_amount), 0))
                .where(Sa.year_quarter == year_quarter, Sa.region_code.is_not(None), Sa.service_industry_code.in_(industry_of))
                .group_by(Sa.region_code, Sa.service_industry_code)
            ).all()
            stores = session.execute(
                select(St.region_code, St.service_industry_code, func.coalesce(func.sum(St.store_count), 0))
                .where(St.year_quarter == year_quarter, St.region_code.is_not(None), St.service_industry_code.in_(industry_of))
                .group_by(St.region_code, St.service_industry_code)
            ).all()
        store_of = {(region, code): int(n) for region, code, n in stores}
        acc: dict[tuple[str, str], list[int]] = {}
        for region, code, amount in amounts:  # 매출이 있는 코드만 — 점포수도 같은 코드에서만 센다
            cell = acc.setdefault((region, industry_of[code]), [0, 0])
            cell[0] += int(amount)
            cell[1] += store_of.get((region, code), 0)
        return {key: (amount, n) for key, (amount, n) in acc.items()}
