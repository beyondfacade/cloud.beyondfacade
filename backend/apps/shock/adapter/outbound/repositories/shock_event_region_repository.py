from sqlalchemy import delete, select

from apps.shock.adapter.outbound.orm_mappers.shock_event_orm_mapper import to_entity
from apps.shock.adapter.outbound.orms.shock_event_orm import ShockEventOrm
from apps.shock.adapter.outbound.orms.shock_event_region_orm import ShockEventRegionOrm
from apps.shock.app.ports.output.shock_event_region_port import (
    ShockEventRegionRepositoryPort,
)
from apps.shock.domain.entities.shock_event_entity import ShockEvent
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyShockEventRegionRepository(ShockEventRegionRepositoryPort):
    def replace_links(self, links: list[tuple[str, str]]) -> int:
        if not links:
            return 0
        with session_scope() as session:
            session.execute(
                delete(ShockEventRegionOrm).where(
                    ShockEventRegionOrm.event_id.in_({event_id for event_id, _ in links})
                )
            )
            session.add_all(
                ShockEventRegionOrm(event_id=event_id, region_code=region_code)
                for event_id, region_code in dict.fromkeys(links)
            )
        return len(links)

    def list_by_region(self, region_code: str) -> list[ShockEvent]:
        with session_scope() as session:
            orms = session.execute(
                select(ShockEventOrm)
                .join(ShockEventRegionOrm, ShockEventRegionOrm.event_id == ShockEventOrm.event_id)
                .where(ShockEventRegionOrm.region_code == region_code)
                .order_by(ShockEventOrm.start_date.desc(), ShockEventOrm.event_id)
            ).scalars()
            return [to_entity(orm, []) for orm in orms]  # 지역 이벤트는 업종 영향 행이 없다
