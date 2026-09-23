"""Driven Adapter — Agent 도구가 필요로 하는 타 BC 사실 조회 (cross-BC 접근은 이 파일 안에서만)."""

from dataclasses import asdict

from sqlalchemy import select

from apps.agent.app.ports.output.agent_port import RegionFactsPort
from apps.agent.domain.value_objects.neighborhood_vocabulary import (
    block_name,
    facility_name,
    label_name,
    type_name,
)
from apps.master.adapter.outbound.orms.population_stat_orm import PopulationStatOrm
from apps.master.dependencies.region_dependencies import get_region_use_case
from apps.metric.adapter.outbound.orms.region_industry_metric_orm import (
    RegionIndustryMetricOrm,
)
from apps.metric.adapter.outbound.orms.region_profile_quarter_orm import (
    RegionProfileQuarterOrm,
)
from apps.neighborhood.adapter.outbound.orms.region_commerce_change_orm import (
    RegionCommerceChangeOrm,
)
from apps.neighborhood.adapter.outbound.orms.region_facility_quarter_orm import (
    RegionFacilityQuarterOrm,
)
from apps.neighborhood.adapter.outbound.orms.region_footfall_quarter_orm import (
    RegionFootfallQuarterOrm,
)
from apps.neighborhood.adapter.outbound.orms.region_housing_average_quarter_orm import (
    RegionHousingAverageQuarterOrm,
)
from apps.shock.adapter.outbound.orms.interest_rate_orm import InterestRateOrm
from apps.shock.app.dtos.shock_event_dto import ShockEventDto
from apps.shock.dependencies.shock_event_dependencies import get_shock_event_use_case
from core.matrix.grid_oracle_database_manager import session_scope

_SCHOOL_AGE_FROM = (5, 10, 15)  # 5년 구간 3개 = 5~19세 학령인구

_TOP_FACILITY_COUNT = 5
# 집객시설 `total`은 19종 합보다 큰 더 넓은 정의다 — 구성 목록과 나란히 놓지 않는다
_EXCLUDED_FACILITY_TYPES = ("total",)


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

    def neighborhood_profile(self, region_code: str) -> dict:
        """market 섹션 슬롯 6종의 재료를 한 번에 모은다 (파생 지표 + 동네 맥락).

        수치를 그대로 넘기는 대신 `caveats`에 해석 주의를 함께 넘긴다. LLM은 결측을 0으로,
        이상치를 대표값으로 읽는 실수를 잘 한다 — 원천이 아는 것을 알려주는 편이 싸다.
        """
        with session_scope() as session:
            profile = session.execute(
                select(RegionProfileQuarterOrm)
                .where(RegionProfileQuarterOrm.region_code == region_code)
                .order_by(RegionProfileQuarterOrm.year_quarter.desc())
                .limit(1)
            ).scalar_one_or_none()
            if profile is None:
                return {}
            quarter = profile.year_quarter
            top_facilities = self._top_facilities(session, region_code, quarter)
            return {
                "region_code": region_code,
                "year_quarter": quarter,
                "type_code": profile.neighborhood_type,
                "type_name": type_name(profile.neighborhood_type),
                "type_reason": profile.type_reason,
                "time_label": label_name(profile.time_label),
                "peak_block": block_name(profile.peak_block),
                "trough_block": block_name(profile.trough_block),
                "footfall_age_mix": self._footfall_age_mix(session, region_code, quarter),
                "worker_resident_ratio": profile.worker_resident_ratio,
                "weekend_index": profile.weekend_index,
                "night_index": profile.night_index,
                "fnb_share": profile.fnb_share,
                "facility_total": profile.facility_total,
                "resident_total": profile.resident_total,
                "commerce_change": self._commerce_change(session, region_code),
                "top_facilities": top_facilities,
                "apartment_avg_price_won": self._apartment_avg_price(
                    session, region_code, quarter
                ),
                "caveats": _profile_caveats(profile, top_facilities),
            }

    @staticmethod
    def _footfall_age_mix(session, region_code: str, quarter: str) -> list[dict]:
        """유동인구 연령 6구간 비중 — 큰 순서. 6구간이 완전 분할이라 합이 분모가 된다."""
        rows = session.execute(
            select(
                RegionFootfallQuarterOrm.dim_key, RegionFootfallQuarterOrm.headcount
            ).where(
                RegionFootfallQuarterOrm.region_code == region_code,
                RegionFootfallQuarterOrm.year_quarter == quarter,
                RegionFootfallQuarterOrm.dim_type == "age",
            )
        ).all()
        counts = {key: value for key, value in rows if value is not None}
        total = sum(counts.values())
        if total == 0:
            return []
        return sorted(
            (
                {"age": key, "share": round(value / total, 4)}
                for key, value in counts.items()
            ),
            key=lambda item: item["share"],
            reverse=True,
        )

    @staticmethod
    def _commerce_change(session, region_code: str) -> dict | None:
        row = session.execute(
            select(RegionCommerceChangeOrm)
            .where(RegionCommerceChangeOrm.region_code == region_code)
            .order_by(RegionCommerceChangeOrm.year_quarter.desc())
            .limit(1)
        ).scalar_one_or_none()
        if row is None:
            return None
        return {
            "code": row.change_code,
            "name": row.change_name,
            "operating_months": row.operating_months,
            "closed_months": row.closed_months,
        }

    @staticmethod
    def _top_facilities(session, region_code: str, quarter: str) -> list[dict]:
        rows = session.execute(
            select(
                RegionFacilityQuarterOrm.facility_type,
                RegionFacilityQuarterOrm.facility_count,
            ).where(
                RegionFacilityQuarterOrm.region_code == region_code,
                RegionFacilityQuarterOrm.year_quarter == quarter,
                RegionFacilityQuarterOrm.facility_type.not_in(_EXCLUDED_FACILITY_TYPES),
                RegionFacilityQuarterOrm.facility_count.is_not(None),
            )
        ).all()
        top = sorted(
            ((facility_type, count) for facility_type, count in rows if count > 0),
            key=lambda item: item[1],
            reverse=True,
        )[:_TOP_FACILITY_COUNT]
        return [{"type": facility_name(t), "count": c} for t, c in top]

    @staticmethod
    def _apartment_avg_price(session, region_code: str, quarter: str) -> int | None:
        return session.execute(
            select(RegionHousingAverageQuarterOrm.avg_price).where(
                RegionHousingAverageQuarterOrm.region_code == region_code,
                RegionHousingAverageQuarterOrm.year_quarter == quarter,
            )
        ).scalar_one_or_none()


def _profile_caveats(profile, top_facilities: list[dict]) -> list[str]:
    """원천이 아는 해석 주의 — LLM이 결측을 0으로 읽지 않게 한다.

    해당하지 않는 주의는 넣지 않는다. 늘 붙는 문구는 읽히지 않는다.
    """
    caveats = []
    if profile.worker_resident_ratio is None:
        caveats.append(
            "이 동은 원천에 직장인구가 없다(서울 11개 동). 0명으로 읽지 말고 직장인구를 언급하지 마라."
        )
    if "재건축" in (profile.type_reason or ""):
        caveats.append(
            "상주인구가 비정상적으로 적어 1인당·비율 지표를 신뢰할 수 없다. 비율로 단정하지 마라."
        )
    caveats.append(
        "아파트 평균 시가는 동별 편차가 극단적이라 참고값이다. 대표 시세로 단정하지 마라."
    )
    if top_facilities and top_facilities[0]["type"] == "버스정거장":
        caveats.append(
            "집객시설 1위가 버스정거장이다. 시설 수를 상권 매력도로 직결해 읽지 마라."
        )
    return caveats
