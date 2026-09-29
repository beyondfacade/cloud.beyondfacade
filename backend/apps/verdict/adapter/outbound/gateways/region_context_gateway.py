"""Driven Adapter — 동 맥락: 최신 분기 상주인구(region_profile_quarter), 최신 분기 상권변화지표(+서울 베이스라인),
최신 연도 점포수(region_industry_metric). 전 행정동(region 마스터) 1행씩 돌려주고 없는 값은 None.
quarter_max·year_max 상한은 백테스트용 — 그 시점까지의 '최신'을 본다(설계서 §13). None이면 현행 최신."""

from sqlalchemy import and_, func, select, true

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.metric.adapter.outbound.orms.region_industry_metric_orm import RegionIndustryMetricOrm
from apps.metric.adapter.outbound.orms.region_profile_quarter_orm import RegionProfileQuarterOrm
from apps.neighborhood.adapter.outbound.orms.region_commerce_change_orm import RegionCommerceChangeOrm
from apps.neighborhood.adapter.outbound.orms.seoul_commerce_change_baseline_orm import (
    SeoulCommerceChangeBaselineOrm,
)
from apps.verdict.app.dtos.region_industry_verdict_dto import LatestStoreCount, RegionContext
from apps.verdict.app.ports.output.region_industry_verdict_port import RegionContextPort
from core.matrix.grid_oracle_database_manager import session_scope


class RegionContextGateway(RegionContextPort):
    def latest_contexts(self, quarter_max: str | None = None) -> list[RegionContext]:
        P, C, B = RegionProfileQuarterOrm, RegionCommerceChangeOrm, SeoulCommerceChangeBaselineOrm
        with session_scope() as session:
            latest_profile = (
                select(P.region_code, func.max(P.year_quarter).label("yq"))
                .where(true() if quarter_max is None else P.year_quarter <= quarter_max)
                .group_by(P.region_code)
                .subquery()
            )
            residents = dict(
                session.execute(
                    select(P.region_code, P.resident_total).join(
                        latest_profile, and_(P.region_code == latest_profile.c.region_code, P.year_quarter == latest_profile.c.yq)
                    )
                ).all()
            )
            latest_change = (
                select(C.region_code, func.max(C.year_quarter).label("yq"))
                .where(C.region_code.is_not(None), true() if quarter_max is None else C.year_quarter <= quarter_max)
                .group_by(C.region_code)
                .subquery()
            )
            change_rows = session.execute(
                select(C.region_code, C.year_quarter, C.change_code, C.change_name, C.closed_months, B.seoul_closed_months)
                .join(latest_change, and_(C.region_code == latest_change.c.region_code, C.year_quarter == latest_change.c.yq))
                .join(B, B.year_quarter == C.year_quarter, isouter=True)
                .order_by(C.region_code, C.adstrd_code)
            ).all()
            changes = {}
            for row in change_rows:
                changes.setdefault(row.region_code, row)  # 한 동에 상권코드가 여럿이면 첫 행(adstrd_code 순)
            region_codes = session.execute(select(RegionOrm.region_code).order_by(RegionOrm.region_code)).scalars().all()
        contexts = []
        for code in region_codes:
            change = changes.get(code)
            contexts.append(RegionContext(
                region_code=code,
                resident_total=residents.get(code),
                change_code=change.change_code if change else None,
                change_name=change.change_name if change else None,
                change_quarter=change.year_quarter if change else None,
                closed_months=change.closed_months if change else None,
                seoul_closed_months=change.seoul_closed_months if change else None,
            ))
        return contexts

    def latest_store_counts(self, year_max: int | None = None) -> list[LatestStoreCount]:
        M = RegionIndustryMetricOrm
        with session_scope() as session:
            latest_year = session.execute(
                select(func.max(M.year)).where(true() if year_max is None else M.year <= year_max)
            ).scalar_one()
            rows = session.execute(
                select(M.region_code, M.industry_id, M.store_count).where(M.year == latest_year)
            ).all()
        return [LatestStoreCount(r, i, n) for r, i, n in rows]
