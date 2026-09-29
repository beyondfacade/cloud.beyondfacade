"""Driven Adapter — 진입 코호트 결과: [as_of, as_of+entry_days) 개업 점포 중 개업 후 horizon_days 안에 폐업한 수 (설계서 §13)."""

from datetime import date, timedelta

from sqlalchemy import and_, func, select

from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from apps.verdict.app.dtos.region_industry_verdict_dto import EntrantOutcome
from apps.verdict.app.ports.output.region_industry_verdict_port import EntrantOutcomePort
from core.matrix.grid_oracle_database_manager import session_scope


class EntrantOutcomeGateway(EntrantOutcomePort):
    def entrant_outcomes(self, as_of: date, entry_days: int, horizon_days: int) -> list[EntrantOutcome]:
        days_open = StoreOrm.close_date - StoreOrm.open_date
        closed_within = and_(StoreOrm.close_date.is_not(None), days_open >= 0, days_open <= horizon_days)
        with session_scope() as session:
            rows = session.execute(
                select(StoreOrm.region_code, StoreOrm.industry_id, func.count(), func.count().filter(closed_within))
                .where(
                    StoreOrm.region_code.is_not(None),
                    StoreOrm.open_date >= as_of,
                    StoreOrm.open_date < as_of + timedelta(days=entry_days),
                )
                .group_by(StoreOrm.region_code, StoreOrm.industry_id)
            ).all()
        return [EntrantOutcome(region, industry, opened, closed) for region, industry, opened, closed in rows]
