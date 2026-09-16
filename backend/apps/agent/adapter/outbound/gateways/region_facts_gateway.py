"""Driven Adapter — Agent 도구가 필요로 하는 타 BC 사실 조회 (cross-BC 접근은 이 파일 안에서만)."""

from dataclasses import asdict

from sqlalchemy import select

from apps.agent.app.ports.output.agent_port import RegionFactsPort
from apps.master.adapter.outbound.orms.population_stat_orm import PopulationStatOrm
from apps.master.dependencies.region_dependencies import get_region_use_case
from apps.metric.adapter.outbound.orms.region_industry_metric_orm import (
    RegionIndustryMetricOrm,
)
from apps.shock.adapter.outbound.orms.interest_rate_orm import InterestRateOrm
from apps.shock.app.dtos.shock_event_dto import ShockEventDto
from apps.shock.dependencies.shock_event_dependencies import get_shock_event_use_case
from core.matrix.grid_oracle_database_manager import session_scope

_SCHOOL_AGE_FROM = (5, 10, 15)  # 5년 구간 3개 = 5~19세 학령인구


def _shock_event_to_dict(dto: ShockEventDto) -> dict:
    return {
        "event_id": dto.event_id,
        "layer": dto.layer,
        "name": dto.name,
        "start_date": dto.start_date.isoformat(),
        "scope": dto.scope,
        "source": dto.source,
        "end_date": dto.end_date.isoformat() if dto.end_date else None,
        "source_url": dto.source_url,
        "description": dto.description,
        "industry_impacts": [
            {"industry_id": i.industry_id, "severity": i.severity}
            for i in dto.industry_impacts
        ],
    }


class RegionFactsGateway(RegionFactsPort):
    """metric·master·shock BC를 조회해 Agent 도구에 dict로 전달 (ACL)."""

    def metrics(self, region_code: str, industry: str) -> list[dict]:
        with session_scope() as session:
            rows = session.execute(
                select(RegionIndustryMetricOrm)
                .where(
                    RegionIndustryMetricOrm.region_code == region_code,
                    RegionIndustryMetricOrm.industry_id == industry,
                )
                .order_by(RegionIndustryMetricOrm.year)
            ).scalars()
            return [
                {
                    "year": row.year,
                    "store_count": row.store_count,
                    "open_count": row.open_count,
                    "close_count": row.close_count,
                    "closure_rate": row.closure_rate,
                    "growth_rate": row.growth_rate,
                }
                for row in rows
            ]

    def summary(self, region_code: str, industry_id: str) -> dict:
        dto = get_region_use_case().summary(region_code, industry_id)
        return asdict(dto)

    def population(self, region_code: str) -> dict:
        with session_scope() as session:
            latest_period = session.execute(
                select(PopulationStatOrm.period)
                .where(PopulationStatOrm.region_code == region_code)
                .order_by(PopulationStatOrm.period.desc())
                .limit(1)
            ).scalar_one_or_none()
            if latest_period is None:
                return {
                    "region_code": region_code,
                    "period": None,
                    "age_distribution": {},
                    "school_age_population": 0,
                }
            rows = session.execute(
                select(PopulationStatOrm).where(
                    PopulationStatOrm.region_code == region_code,
                    PopulationStatOrm.period == latest_period,
                )
            ).scalars()
            age_distribution: dict[int, int] = {}
            school_age_population = 0
            for row in rows:
                age_distribution[row.age_from] = (
                    age_distribution.get(row.age_from, 0) + row.population
                )
                if row.age_from in _SCHOOL_AGE_FROM:
                    school_age_population += row.population
            return {
                "region_code": region_code,
                "period": latest_period,
                "age_distribution": age_distribution,
                "school_age_population": school_age_population,
            }

    def shocks(self, industry_id: str | None, limit: int) -> list[dict]:
        events = get_shock_event_use_case().list_events(industry_id, limit)
        return [_shock_event_to_dict(e) for e in events]

    def latest_rates(self) -> dict:
        with session_scope() as session:
            rows = session.execute(select(InterestRateOrm)).scalars()
            latest: dict[str, tuple[str, float]] = {}
            for row in rows:
                current = latest.get(row.rate_type)
                if current is None or row.period > current[0]:
                    latest[row.rate_type] = (row.period, row.rate)
            return {rate_type: rate for rate_type, (_, rate) in latest.items()}
