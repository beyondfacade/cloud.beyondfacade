"""Driven Adapter — shock BC의 ECOS 금리에서 시설자금대출(`loan_facility`) 최신값."""

from sqlalchemy import select

from apps.finance.app.dtos.finance_dto import RateBasis
from apps.finance.app.ports.output.finance_port import LoanRateFactsPort
from apps.shock.adapter.outbound.orms.interest_rate_orm import InterestRateOrm
from core.matrix.grid_oracle_database_manager import session_scope

_RATE_TYPE = "loan_facility"  # ECOS 121Y006 시설자금 — 상가 관련 최근접 계열


class LoanRateFactsGateway(LoanRateFactsPort):
    def latest_facility_rate(self) -> RateBasis | None:
        with session_scope() as session:
            row = session.execute(
                select(InterestRateOrm.period, InterestRateOrm.rate)
                .where(InterestRateOrm.rate_type == _RATE_TYPE)
                .order_by(InterestRateOrm.period.desc())
                .limit(1)
            ).one_or_none()
        if row is None:
            return None
        period, rate = row
        return RateBasis(rate_type=_RATE_TYPE, period=period, rate_pct=float(rate))
