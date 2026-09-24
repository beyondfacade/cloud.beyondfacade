"""Driven Adapter — store 원천 테이블 연도별 집계 (cross-BC 접근은 어댑터 레이어에서만)."""

from datetime import date

from sqlalchemy import func, or_, select

from apps.metric.app.dtos.region_industry_metric_dto import YearlyStoreStat
from apps.metric.app.ports.output.region_industry_metric_port import StoreStatsPort
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from core.matrix.grid_oracle_database_manager import session_scope

# 폐업 이력이 없는 원천 — 서울 학원 API(OA-20528)는 폐원일자를 주지 않아 close_date가 전부 NULL이다.
# 그 0건을 폐업 0으로 세면 폐업률 0.0이 값처럼 보인다 → 스냅샷 원천(어린이집·편의점)과 같이 None으로 둔다.
_NO_CLOSURE_HISTORY = frozenset({"academy"})


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
                        close_count=None if industry_id in _NO_CLOSURE_HISTORY else close_count,
                    )
                    for region_code, industry_id, store_count, open_count, close_count in rows
                )
        return stats
