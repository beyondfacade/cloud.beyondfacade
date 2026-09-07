from dataclasses import replace

from sqlalchemy import delete, select

from apps.shock.adapter.outbound.orm_mappers.shock_event_orm_mapper import (
    apply_to_orm,
    to_entity,
    to_impact_orms,
    to_orm,
)
from apps.shock.adapter.outbound.orms.shock_event_industry_orm import (
    ShockEventIndustryOrm,
)
from apps.shock.adapter.outbound.orms.shock_event_orm import ShockEventOrm
from apps.shock.app.ports.output.shock_event_port import ShockEventRepositoryPort
from apps.shock.domain.entities.shock_event_entity import ShockEvent
from core.matrix.grid_oracle_database_manager import session_scope


def _normalized(event: ShockEvent) -> ShockEvent:
    """비교용 정규화 — 업종 영향 순서 차이를 무시한다."""
    return replace(
        event,
        industry_impacts=sorted(event.industry_impacts, key=lambda i: i.industry_id),
    )


class SqlAlchemyShockEventRepository(ShockEventRepositoryPort):
    def upsert(self, events: list[ShockEvent]) -> tuple[int, int]:
        if not events:
            return 0, 0
        batch = {e.event_id: _normalized(e) for e in events}  # 배치 내 중복 제거
        inserted = updated = 0
        with session_scope() as session:
            existing = {
                orm.event_id: orm
                for orm in session.execute(
                    select(ShockEventOrm).where(
                        ShockEventOrm.event_id.in_(batch.keys())
                    )
                ).scalars()
            }
            impacts_by_event: dict[str, list[ShockEventIndustryOrm]] = {}
            for impact_orm in session.execute(
                select(ShockEventIndustryOrm).where(
                    ShockEventIndustryOrm.event_id.in_(batch.keys())
                )
            ).scalars():
                impacts_by_event.setdefault(impact_orm.event_id, []).append(impact_orm)
            for event_id, event in batch.items():
                orm = existing.get(event_id)
                if orm is None:
                    session.add(to_orm(event))
                    session.flush()  # FK 순서 보장 — 부모(shock_event) 먼저 INSERT
                    session.add_all(to_impact_orms(event))
                    inserted += 1
                    continue
                if to_entity(orm, impacts_by_event.get(event_id, [])) == event:
                    continue  # 내용 동일 — 무변경 (재실행 멱등)
                apply_to_orm(event, orm)
                session.execute(
                    delete(ShockEventIndustryOrm).where(
                        ShockEventIndustryOrm.event_id == event_id
                    )
                )
                session.add_all(to_impact_orms(event))  # 업종 영향 행 교체
                updated += 1
        return inserted, updated

    def list_events(self, industry_id: str | None, limit: int) -> list[ShockEvent]:
        with session_scope() as session:
            statement = (
                select(ShockEventOrm)
                .order_by(ShockEventOrm.start_date, ShockEventOrm.event_id)
                .limit(limit)
            )
            if industry_id is not None:
                statement = statement.join(
                    ShockEventIndustryOrm,
                    ShockEventIndustryOrm.event_id == ShockEventOrm.event_id,
                ).where(ShockEventIndustryOrm.industry_id == industry_id)
            orms = list(session.execute(statement).scalars())
            impacts_by_event: dict[str, list[ShockEventIndustryOrm]] = {}
            for impact_orm in session.execute(
                select(ShockEventIndustryOrm).where(
                    ShockEventIndustryOrm.event_id.in_([o.event_id for o in orms])
                )
            ).scalars():
                impacts_by_event.setdefault(impact_orm.event_id, []).append(impact_orm)
            return [
                to_entity(orm, impacts_by_event.get(orm.event_id, [])) for orm in orms
            ]
