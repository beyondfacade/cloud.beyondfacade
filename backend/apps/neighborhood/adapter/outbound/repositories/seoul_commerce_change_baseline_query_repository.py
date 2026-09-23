from apps.neighborhood.adapter.outbound.orm_mappers.seoul_commerce_change_baseline_orm_mapper import (
    to_entity,
)
from apps.neighborhood.adapter.outbound.orms.seoul_commerce_change_baseline_orm import (
    SeoulCommerceChangeBaselineOrm,
)
from apps.neighborhood.app.ports.output.seoul_commerce_change_baseline_query_port import (
    SeoulCommerceChangeBaselineQueryPort,
)
from apps.neighborhood.domain.entities.seoul_commerce_change_baseline_entity import (
    SeoulCommerceChangeBaseline,
)
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemySeoulCommerceChangeBaselineQueryRepository(SeoulCommerceChangeBaselineQueryPort):
    def find(self, year_quarter: str) -> SeoulCommerceChangeBaseline | None:
        with session_scope() as session:
            orm = session.get(SeoulCommerceChangeBaselineOrm, year_quarter)
            return None if orm is None else to_entity(orm)
