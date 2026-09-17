from apps.childcare.adapter.outbound.orm_mappers.childcare_center_stat_orm_mapper import to_entity
from apps.childcare.adapter.outbound.repositories.childcare_center_repository import (
    operating_centers_with_latest_stat,
)
from apps.childcare.app.ports.output.childcare_center_stat_port import (
    ChildcareCenterStatRepositoryPort,
)
from apps.childcare.domain.entities.childcare_center_stat_entity import ChildcareCenterStat
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyChildcareCenterStatRepository(ChildcareCenterStatRepositoryPort):
    def list_latest(self, region_code: str) -> list[ChildcareCenterStat]:
        with session_scope() as session:
            rows = session.execute(operating_centers_with_latest_stat(region_code)).all()
            return [to_entity(stat) for _, stat in rows]
