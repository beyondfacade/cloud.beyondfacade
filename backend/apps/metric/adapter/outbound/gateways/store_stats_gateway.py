"""Driven Adapter — store 원천 테이블 연도별 집계 (cross-BC 접근은 어댑터 레이어에서만)."""

from datetime import date

from sqlalchemy import func, or_, select

from apps.metric.app.dtos.region_industry_metric_dto import YearlyStoreStat
from apps.metric.app.ports.output.region_industry_metric_port import StoreStatsPort
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from core.matrix.grid_oracle_database_manager import session_scope


class StoreStatsGateway(StoreStatsPort):
    def yearly_stats(self, years: list[int]) -> list[YearlyStoreStat]:
        stats: list[YearlyStoreStat] = []
        with session_scope() as session:
            for year in years:
                end_of_year = date(year, 12, 31)
                rows = session.execute(
                    select(
                        StoreOrm.region_code,
                        StoreOrm.industry_id,
                        # 연도 말 기준 영업 중: 개업 이후 & (미폐업 or 이듬해 이후 폐업)
                        func.count().filter(
                            StoreOrm.open_date <= end_of_year,
                            or_(
                                StoreOrm.close_date.is_(None),
                                StoreOrm.close_date > end_of_year,
                            ),
                        ),
                        func.count().filter(
                            func.extract("year", StoreOrm.open_date) == year
                        ),
                        func.count().filter(
                            func.extract("year", StoreOrm.close_date) == year
                        ),
                    )
                    .where(StoreOrm.region_code.is_not(None))
                    .group_by(StoreOrm.region_code, StoreOrm.industry_id)
                ).all()
                stats.extend(
                    YearlyStoreStat(
                        region_code=region_code,
                        industry_id=industry_id,
                        year=year,
                        store_count=store_count,
                        open_count=open_count,
                        close_count=close_count,
                    )
                    for region_code, industry_id, store_count, open_count, close_count in rows
                )
        return stats
