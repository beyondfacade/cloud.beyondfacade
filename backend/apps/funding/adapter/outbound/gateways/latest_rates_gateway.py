"""Driven Adapter — shock BC의 ECOS 금리에서 계열별 최신월 (cross-BC 접근은 이 파일 안에서만)."""

from sqlalchemy import func, select

from apps.funding.app.dtos.funding_program_dto import RateDto
from apps.funding.app.ports.output.funding_program_port import LatestRatesPort
from apps.shock.adapter.outbound.orms.interest_rate_orm import InterestRateOrm
from core.matrix.grid_oracle_database_manager import session_scope

# 기준금리 · 시설자금대출(121Y006, 상가 관련 최근접 계열) — 화면이 이 순서로 보여준다
RATE_TYPES: tuple[str, ...] = ("base", "loan_facility")


class LatestRatesGateway(LatestRatesPort):
    def latest(self) -> list[RateDto]:
        with session_scope() as session:
            latest_period = (
                select(InterestRateOrm.rate_type, func.max(InterestRateOrm.period).label("period"))
                .where(InterestRateOrm.rate_type.in_(RATE_TYPES))
                .group_by(InterestRateOrm.rate_type)
                .subquery()
            )
            rows = session.execute(
                select(InterestRateOrm.rate_type, InterestRateOrm.period, InterestRateOrm.rate).join(
                    latest_period,
                    (InterestRateOrm.rate_type == latest_period.c.rate_type)
                    & (InterestRateOrm.period == latest_period.c.period),
                )
            ).all()
        found = {rate_type: RateDto(rate_type, period, float(rate)) for rate_type, period, rate in rows}
        return [found[rate_type] for rate_type in RATE_TYPES if rate_type in found]
