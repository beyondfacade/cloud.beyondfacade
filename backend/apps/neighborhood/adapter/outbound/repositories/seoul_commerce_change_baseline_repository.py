from sqlalchemy.dialects.postgresql import insert

from apps.neighborhood.adapter.outbound.orm_mappers.seoul_commerce_change_baseline_orm_mapper import (
    to_row,
)
from apps.neighborhood.adapter.outbound.orms.seoul_commerce_change_baseline_orm import (
    SeoulCommerceChangeBaselineOrm,
)
from apps.neighborhood.app.ports.output.seoul_commerce_change_baseline_port import (
    SeoulCommerceChangeBaselineRepositoryPort,
)
from apps.neighborhood.domain.entities.seoul_commerce_change_baseline_entity import (
    SeoulCommerceChangeBaseline,
)
from core.matrix.grid_oracle_database_manager import session_scope

_PK = ("year_quarter",)
_BATCH = 20000  # 3컬럼 × 20000 = 60,000 파라미터 < psycopg 한도 65,535


class SqlAlchemySeoulCommerceChangeBaselineRepository(SeoulCommerceChangeBaselineRepositoryPort):
    def upsert(self, rows: list[SeoulCommerceChangeBaseline]) -> int:
        """PK 충돌 시 값 컬럼만 갱신 — 같은 원천을 두 번 돌려도 행 수가 변하지 않는다."""
        if not rows:
            return 0
        count = 0
        with session_scope() as session:
            for start in range(0, len(rows), _BATCH):
                values = [to_row(row) for row in rows[start : start + _BATCH]]
                statement = insert(SeoulCommerceChangeBaselineOrm).values(values)
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
