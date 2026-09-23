"""Driven Adapters — 시간대 어긋남의 두 원천 (cross-BC 접근은 어댑터에서만).

유동인구는 neighborhood, 매출은 commerce에서 읽는다. 두 원천의 시간 구간 어휘가 같은 값으로
정규화돼 있어(`00_06`) 구분자 차이로 어긋나지 않는다.
"""

from collections import defaultdict

from sqlalchemy import and_, func, select

from apps.commerce.adapter.outbound.orms.region_commerce_sales_breakdown_orm import (
    RegionCommerceSalesBreakdownOrm,
)
from apps.master.adapter.outbound.orms.industry_source_code_orm import (
    IndustrySourceCodeOrm,
)
from apps.metric.app.dtos.region_industry_hour_gap_dto import (
    RegionHourValues,
    RegionIndustryHourSales,
)
from apps.metric.app.ports.output.region_industry_hour_gap_port import (
    RegionFootfallHourPort,
    RegionIndustryHourSalesPort,
)
from apps.neighborhood.adapter.outbound.orms.region_footfall_quarter_orm import (
    RegionFootfallQuarterOrm,
)
from core.matrix.grid_oracle_database_manager import session_scope

_SOURCE_SYSTEM = "seoul_commercial"


class RegionFootfallHourGateway(RegionFootfallHourPort):
    def hour_values(self, quarters: list[str]) -> list[RegionHourValues]:
        if not quarters:
            return []
        values: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
        with session_scope() as session:
            rows = session.execute(
                select(
                    RegionFootfallQuarterOrm.region_code,
                    RegionFootfallQuarterOrm.year_quarter,
                    RegionFootfallQuarterOrm.dim_key,
                    RegionFootfallQuarterOrm.headcount,
                ).where(
                    RegionFootfallQuarterOrm.dim_type == "hour",
                    RegionFootfallQuarterOrm.region_code.is_not(None),
                    RegionFootfallQuarterOrm.year_quarter.in_(quarters),
                )
            ).all()
        for region_code, year_quarter, band, headcount in rows:
            if headcount is not None:
                values[(region_code, year_quarter)][band] = float(headcount)
        return [
            RegionHourValues(region_code=region_code, year_quarter=year_quarter, values=bands)
            for (region_code, year_quarter), bands in sorted(values.items())
        ]


class RegionIndustryHourSalesGateway(RegionIndustryHourSalesPort):
    """여러 CS 코드가 한 업종에 붙는 경우(academy 4 · cafe 3 · hair_salon 3)를 SQL에서 합산한다."""

    def hour_sales(self, quarters: list[str]) -> list[RegionIndustryHourSales]:
        if not quarters:
            return []
        values: dict[tuple[str, str, str], dict[str, float]] = defaultdict(dict)
        with session_scope() as session:
            rows = session.execute(
                select(
                    RegionCommerceSalesBreakdownOrm.region_code,
                    IndustrySourceCodeOrm.industry_id,
                    RegionCommerceSalesBreakdownOrm.year_quarter,
                    RegionCommerceSalesBreakdownOrm.dim_key,
                    func.sum(RegionCommerceSalesBreakdownOrm.amount),
                )
                .join(
                    IndustrySourceCodeOrm,
                    and_(
                        IndustrySourceCodeOrm.code
                        == RegionCommerceSalesBreakdownOrm.service_industry_code,
                        IndustrySourceCodeOrm.source_system == _SOURCE_SYSTEM,
                    ),
                )
                .where(
                    RegionCommerceSalesBreakdownOrm.dim_type == "hour",
                    RegionCommerceSalesBreakdownOrm.region_code.is_not(None),
                    RegionCommerceSalesBreakdownOrm.year_quarter.in_(quarters),
                )
                .group_by(
                    RegionCommerceSalesBreakdownOrm.region_code,
                    IndustrySourceCodeOrm.industry_id,
                    RegionCommerceSalesBreakdownOrm.year_quarter,
                    RegionCommerceSalesBreakdownOrm.dim_key,
                )
            ).all()
        for region_code, industry_id, year_quarter, band, amount in rows:
            if amount is not None:
                values[(region_code, industry_id, year_quarter)][band] = float(amount)
        return [
            RegionIndustryHourSales(
                region_code=region_code,
                industry_id=industry_id,
                year_quarter=year_quarter,
                values=bands,
            )
            for (region_code, industry_id, year_quarter), bands in sorted(values.items())
        ]
