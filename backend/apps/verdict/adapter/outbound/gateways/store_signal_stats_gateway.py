"""Driven Adapter — store 원천을 한 번의 group_by로 세 집계 (cross-BC 접근은 어댑터 레이어에서만).
창(12개월·3년·4년)은 today 기준 일수로 잡는다 — 월 단위 산술의 2/29 문제를 피한다."""

from datetime import date, timedelta

from sqlalchemy import and_, func, or_, select

from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.verdict.app.dtos.region_industry_verdict_dto import StoreSignalStat
from apps.verdict.app.ports.output.region_industry_verdict_port import StoreSignalStatsPort
from core.matrix.grid_oracle_database_manager import session_scope

_DAYS_PER_MONTH = 30.4375
_THREE_YEARS_DAYS = 3 * 365


class StoreSignalStatsGateway(StoreSignalStatsPort):
    def signal_stats(self, today: date) -> list[StoreSignalStat]:
        since_12m = today - timedelta(days=365)
        cohort_to = today - timedelta(days=3 * 365)  # 코호트 = [today−4y, today−3y)
        cohort_from = today - timedelta(days=4 * 365)
        since_3y = cohort_to

        days_open = StoreOrm.close_date - StoreOrm.open_date  # PostgreSQL: date − date = 일수(int)
        in_cohort = and_(StoreOrm.open_date >= cohort_from, StoreOrm.open_date < cohort_to)
        closed_3y = and_(StoreOrm.close_date.is_not(None), StoreOrm.close_date >= since_3y, StoreOrm.close_date <= today)

        with session_scope() as session:
            rows = session.execute(
                select(
                    StoreOrm.region_code,
                    StoreOrm.industry_id,
                    # 12개월 전 시점 영업중: 그 전에 개업 & (미폐업 or 그 뒤 폐업)
                    func.count().filter(
                        StoreOrm.open_date <= since_12m,
                        or_(StoreOrm.close_date.is_(None), StoreOrm.close_date > since_12m),
                    ),
                    func.count().filter(StoreOrm.open_date > since_12m, StoreOrm.open_date <= today),
                    func.count().filter(StoreOrm.close_date > since_12m, StoreOrm.close_date <= today),
                    func.count().filter(in_cohort),
                    func.count().filter(in_cohort, or_(StoreOrm.close_date.is_(None), days_open >= _THREE_YEARS_DAYS)),
                    func.count().filter(closed_3y),
                    func.percentile_cont(0.5).within_group(days_open / _DAYS_PER_MONTH).filter(closed_3y),
                )
                .where(StoreOrm.region_code.is_not(None), StoreOrm.open_date.is_not(None))
                .group_by(StoreOrm.region_code, StoreOrm.industry_id)
            ).all()
        return [
            StoreSignalStat(
                region_code=region_code, industry_id=industry_id, start_store_count=start, opened_12m=opened,
                closed_12m=closed, cohort_size=cohort, cohort_survived=survived, closed_3y_count=closed_3y_count,
                closed_3y_median_months=None if median is None else float(median),
            )
            for region_code, industry_id, start, opened, closed, cohort, survived, closed_3y_count, median in rows
        ]
