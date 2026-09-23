from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from apps.metric.adapter.outbound.orm_mappers.region_profile_orm_mapper import (
    to_entity,
    to_row,
)
from apps.metric.adapter.outbound.orms.region_profile_quarter_orm import (
    RegionProfileQuarterOrm,
)
from apps.metric.app.ports.output.region_profile_port import RegionProfileRepositoryPort
from apps.metric.domain.entities.region_profile_entity import RegionProfile
from core.matrix.grid_oracle_database_manager import session_scope

_PK = ("region_code", "year_quarter")
_BATCH = 3000  # 18컬럼 × 3000 = 54,000 파라미터 < psycopg 한도 65,535 (블록 4컬럼 추가로 4000이면 72,000 초과)


class SqlAlchemyRegionProfileRepository(RegionProfileRepositoryPort):
    def upsert(self, profiles: list[RegionProfile]) -> int:
        """PK 충돌 시 값 컬럼만 갱신 — 규칙을 바꿔 다시 돌려도 행 수가 변하지 않는다."""
        if not profiles:
            return 0
        count = 0
        with session_scope() as session:
            for start in range(0, len(profiles), _BATCH):
                values = [to_row(profile) for profile in profiles[start : start + _BATCH]]
                statement = insert(RegionProfileQuarterOrm).values(values)
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

    def find(self, region_code: str, year_quarter: str) -> RegionProfile | None:
        with session_scope() as session:
            orm = session.get(RegionProfileQuarterOrm, (region_code, year_quarter))
            return None if orm is None else to_entity(orm)

    def find_latest(self, region_code: str) -> RegionProfile | None:
        with session_scope() as session:
            orm = session.execute(
                select(RegionProfileQuarterOrm)
                .where(RegionProfileQuarterOrm.region_code == region_code)
                .order_by(RegionProfileQuarterOrm.year_quarter.desc())
                .limit(1)
            ).scalar_one_or_none()
            return None if orm is None else to_entity(orm)

    def latest_quarter(self) -> str | None:
        with session_scope() as session:
            return session.execute(
                select(RegionProfileQuarterOrm.year_quarter)
                .order_by(RegionProfileQuarterOrm.year_quarter.desc())
                .limit(1)
            ).scalar_one_or_none()

    def list_by_quarter(self, year_quarter: str) -> list[RegionProfile]:
        with session_scope() as session:
            rows = (
                session.execute(
                    select(RegionProfileQuarterOrm)
                    .where(RegionProfileQuarterOrm.year_quarter == year_quarter)
                    .order_by(RegionProfileQuarterOrm.region_code)
                )
                .scalars()
                .all()
            )
            return [to_entity(row) for row in rows]
