from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from apps.metric.adapter.outbound.orm_mappers.region_industry_hour_gap_orm_mapper import (
    to_entity,
    to_row,
)
from apps.metric.adapter.outbound.orms.region_industry_hour_gap_quarter_orm import (
    RegionIndustryHourGapQuarterOrm,
)
from apps.metric.app.ports.output.region_industry_hour_gap_port import (
    RegionIndustryHourGapRepositoryPort,
)
from apps.metric.domain.entities.region_industry_hour_gap_entity import (
    RegionIndustryHourGap,
)
from apps.metric.domain.value_objects.hour_band import HOUR_BANDS
from core.matrix.grid_oracle_database_manager import session_scope

_PK = ("region_code", "industry_id", "year_quarter", "hour_band")
_BATCH = 8000  # 7컬럼 × 8000 = 56,000 파라미터 < psycopg 한도 65,535


class SqlAlchemyRegionIndustryHourGapRepository(RegionIndustryHourGapRepositoryPort):
    def upsert(self, gaps: list[RegionIndustryHourGap]) -> int:
        """PK 충돌 시 값 컬럼만 갱신 — 46만 행을 다시 돌려도 행 수가 변하지 않는다."""
        if not gaps:
            return 0
        count = 0
        with session_scope() as session:
            for start in range(0, len(gaps), _BATCH):
                values = [to_row(gap) for gap in gaps[start : start + _BATCH]]
                statement = insert(RegionIndustryHourGapQuarterOrm).values(values)
                session.execute(
                    statement.on_conflict_do_update(
                        index_elements=list(_PK),
                        set_={
                            column: getattr(statement.excluded, column)
                            for column in values[0]
                            if column not in _PK
                        },
                    )
                )
                count += len(values)
        return count

    def latest_quarter(self, region_code: str, industry_id: str) -> str | None:
        with session_scope() as session:
            return session.execute(
                select(RegionIndustryHourGapQuarterOrm.year_quarter)
                .where(
                    RegionIndustryHourGapQuarterOrm.region_code == region_code,
                    RegionIndustryHourGapQuarterOrm.industry_id == industry_id,
                )
                .order_by(RegionIndustryHourGapQuarterOrm.year_quarter.desc())
                .limit(1)
            ).scalar_one_or_none()

    def list_bands(
        self, region_code: str, industry_id: str, year_quarter: str
    ) -> list[RegionIndustryHourGap]:
        with session_scope() as session:
            rows = (
                session.execute(
                    select(RegionIndustryHourGapQuarterOrm).where(
                        RegionIndustryHourGapQuarterOrm.region_code == region_code,
                        RegionIndustryHourGapQuarterOrm.industry_id == industry_id,
                        RegionIndustryHourGapQuarterOrm.year_quarter == year_quarter,
                    )
                )
                .scalars()
                .all()
            )
            # 시간 순은 문자열 정렬과 일치하지만 구간 어휘를 단일 원천으로 두는 편이 안전하다
            order = {band: index for index, band in enumerate(HOUR_BANDS)}
            return [
                to_entity(row) for row in sorted(rows, key=lambda r: order[r.hour_band])
            ]
