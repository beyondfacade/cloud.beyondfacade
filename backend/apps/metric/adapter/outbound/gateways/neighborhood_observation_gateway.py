"""Driven Adapter — neighborhood BC 원자료에서 판정 입력을 모은다 (cross-BC 접근은 어댑터에서만).

읽기 방향은 metric → neighborhood 단방향이다. 역방향 참조를 만들지 않는다 (설계서 §2).

쓰면 안 되는 값은 손대지 않는다 (설계서 §3-2): `household`의 아파트 가구 수(전 행 0), 집객시설
19종 합(total과 정의가 달라 나란히 놓을 수 없다), `train_station`(전 행 NULL).
"""

from collections import defaultdict

from sqlalchemy import func, select

from apps.metric.app.dtos.region_profile_dto import RegionQuarterObservation
from apps.metric.app.ports.output.region_profile_port import NeighborhoodObservationPort
from apps.neighborhood.adapter.outbound.orms.region_facility_quarter_orm import (
    RegionFacilityQuarterOrm,
)
from apps.neighborhood.adapter.outbound.orms.region_footfall_quarter_orm import (
    RegionFootfallQuarterOrm,
)
from apps.neighborhood.adapter.outbound.orms.region_population_quarter_orm import (
    RegionPopulationQuarterOrm,
)
from apps.neighborhood.adapter.outbound.orms.region_spending_quarter_orm import (
    RegionSpendingQuarterOrm,
)
from core.matrix.grid_oracle_database_manager import session_scope

_Key = tuple[str, str]  # (region_code, year_quarter)


class _Accumulator:
    """동×분기 한 칸에 여러 원천을 모으는 상자."""

    def __init__(self) -> None:
        self.worker_total: int | None = None
        self.resident_total: int | None = None
        self.hours: dict[str, float] = {}
        self.dow: dict[str, float] = {}
        self.footfall_20s: float | None = None
        self.footfall_age_total: float | None = None
        self.spending: dict[str, int] = {}
        self.facility_total: int | None = None
        self.university_count: int | None = None


class NeighborhoodObservationGateway(NeighborhoodObservationPort):
    def quarter_observations(self, quarters: list[str]) -> list[RegionQuarterObservation]:
        if not quarters:
            return []
        cells: dict[_Key, _Accumulator] = defaultdict(_Accumulator)
        with session_scope() as session:
            self._load_population(session, quarters, cells)
            self._load_footfall(session, quarters, cells)
            self._load_spending(session, quarters, cells)
            self._load_facility(session, quarters, cells)
        return [
            RegionQuarterObservation(
                region_code=region_code,
                year_quarter=year_quarter,
                worker_total=cell.worker_total,
                resident_total=cell.resident_total,
                footfall_by_hour=cell.hours,
                footfall_by_dow=cell.dow,
                footfall_20s=cell.footfall_20s,
                footfall_age_total=cell.footfall_age_total,
                spending_total=cell.spending.get("total"),
                # 음식 + 유흥 — 둘 중 하나만 있어도 합산한다
                spending_fnb=_sum_present(
                    cell.spending.get("food"), cell.spending.get("entertainment")
                ),
                facility_total=cell.facility_total,
                university_count=cell.university_count,
            )
            for (region_code, year_quarter), cell in sorted(cells.items())
        ]

    @staticmethod
    def _load_population(session, quarters, cells) -> None:
        rows = session.execute(
            select(
                RegionPopulationQuarterOrm.region_code,
                RegionPopulationQuarterOrm.year_quarter,
                RegionPopulationQuarterOrm.population_type,
                RegionPopulationQuarterOrm.headcount,
            ).where(
                RegionPopulationQuarterOrm.dim_type == "total",
                RegionPopulationQuarterOrm.dim_key == "all",
                RegionPopulationQuarterOrm.region_code.is_not(None),
                RegionPopulationQuarterOrm.year_quarter.in_(quarters),
            )
        ).all()
        # 직장인구는 414개 동뿐이다 — 없는 동은 행이 아예 없고 None으로 남는다 (설계서 §3-4)
        for region_code, year_quarter, population_type, headcount in rows:
            cell = cells[(region_code, year_quarter)]
            setattr(cell, f"{population_type}_total", headcount)

    @staticmethod
    def _load_footfall(session, quarters, cells) -> None:
        rows = session.execute(
            select(
                RegionFootfallQuarterOrm.region_code,
                RegionFootfallQuarterOrm.year_quarter,
                RegionFootfallQuarterOrm.dim_type,
                RegionFootfallQuarterOrm.dim_key,
                RegionFootfallQuarterOrm.headcount,
            ).where(
                RegionFootfallQuarterOrm.dim_type.in_(("hour", "dow", "age")),
                RegionFootfallQuarterOrm.region_code.is_not(None),
                RegionFootfallQuarterOrm.year_quarter.in_(quarters),
            )
        ).all()
        for region_code, year_quarter, dim_type, dim_key, headcount in rows:
            if headcount is None:
                continue
            cell = cells[(region_code, year_quarter)]
            if dim_type == "hour":
                cell.hours[dim_key] = float(headcount)
            elif dim_type == "dow":
                cell.dow[dim_key] = float(headcount)
            else:  # age — 6구간이 완전 분할이라 합이 분모가 된다
                cell.footfall_age_total = (cell.footfall_age_total or 0.0) + float(headcount)
                if dim_key == "20":
                    cell.footfall_20s = float(headcount)

    @staticmethod
    def _load_spending(session, quarters, cells) -> None:
        rows = session.execute(
            select(
                RegionSpendingQuarterOrm.region_code,
                RegionSpendingQuarterOrm.year_quarter,
                RegionSpendingQuarterOrm.spending_category,
                RegionSpendingQuarterOrm.amount,
            ).where(
                RegionSpendingQuarterOrm.spending_category.in_(
                    ("total", "food", "entertainment")
                ),
                RegionSpendingQuarterOrm.region_code.is_not(None),
                RegionSpendingQuarterOrm.year_quarter.in_(quarters),
            )
        ).all()
        for region_code, year_quarter, category, amount in rows:
            if amount is not None:
                cells[(region_code, year_quarter)].spending[category] = amount

    @staticmethod
    def _load_facility(session, quarters, cells) -> None:
        rows = session.execute(
            select(
                RegionFacilityQuarterOrm.region_code,
                RegionFacilityQuarterOrm.year_quarter,
                RegionFacilityQuarterOrm.facility_type,
                func.sum(RegionFacilityQuarterOrm.facility_count),
            )
            .where(
                RegionFacilityQuarterOrm.facility_type.in_(("total", "university")),
                RegionFacilityQuarterOrm.region_code.is_not(None),
                RegionFacilityQuarterOrm.year_quarter.in_(quarters),
            )
            .group_by(
                RegionFacilityQuarterOrm.region_code,
                RegionFacilityQuarterOrm.year_quarter,
                RegionFacilityQuarterOrm.facility_type,
            )
        ).all()
        for region_code, year_quarter, facility_type, count in rows:
            cell = cells[(region_code, year_quarter)]
            if facility_type == "total":
                cell.facility_total = count
            else:
                # 대학 NULL은 "0개"가 아니라 "집계되지 않음"이지만, 규칙이 묻는 것은
                # "대학이 동을 얼마나 차지하느냐"라 판정에서는 없는 것과 같다
                cell.university_count = count


def _sum_present(*values: int | None) -> int | None:
    present = [value for value in values if value is not None]
    return sum(present) if present else None
