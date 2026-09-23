from sqlalchemy.dialects.postgresql import insert

from apps.neighborhood.adapter.outbound.orm_mappers.region_facility_quarter_orm_mapper import (
    to_row,
)
from apps.neighborhood.adapter.outbound.orms.region_facility_quarter_orm import (
    RegionFacilityQuarterOrm,
)
from apps.neighborhood.app.ports.output.region_facility_quarter_port import (
    RegionFacilityQuarterRepositoryPort,
)
from apps.neighborhood.domain.entities.region_facility_quarter_entity import RegionFacilityQuarter
from core.matrix.grid_oracle_database_manager import session_scope

_PK = ("adstrd_code", "year_quarter", "facility_type")
_BATCH = 12000  # 5컬럼 × 12000 = 60,000 파라미터 < psycopg 한도 65,535


class SqlAlchemyRegionFacilityQuarterRepository(RegionFacilityQuarterRepositoryPort):
    def upsert(self, rows: list[RegionFacilityQuarter]) -> int:
        """PK 충돌 시 값 컬럼만 갱신 — 같은 원천을 두 번 돌려도 행 수가 변하지 않는다."""
        if not rows:
            return 0
        count = 0
        with session_scope() as session:
            for start in range(0, len(rows), _BATCH):
                values = [to_row(row) for row in rows[start : start + _BATCH]]
                statement = insert(RegionFacilityQuarterOrm).values(values)
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
