"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.shock.adapter.outbound.orms.shock_event_industry_orm import (
    ShockEventIndustryOrm,
)
from apps.shock.adapter.outbound.orms.shock_event_orm import ShockEventOrm
from apps.shock.domain.entities.shock_event_entity import IndustryImpact, ShockEvent

_FIELDS = (
    "event_id",
    "layer",
    "name",
    "start_date",
    "end_date",
    "scope",
    "source",
    "source_url",
    "description",
)


def to_orm(entity: ShockEvent) -> ShockEventOrm:
    return ShockEventOrm(**{name: getattr(entity, name) for name in _FIELDS})


def to_entity(
    orm: ShockEventOrm, impact_orms: list[ShockEventIndustryOrm]
) -> ShockEvent:
    return ShockEvent(
        **{name: getattr(orm, name) for name in _FIELDS},
        industry_impacts=sorted(
            (IndustryImpact(i.industry_id, i.severity) for i in impact_orms),
            key=lambda impact: impact.industry_id,
        ),
    )


def apply_to_orm(entity: ShockEvent, orm: ShockEventOrm) -> None:
    for name in _FIELDS:
        setattr(orm, name, getattr(entity, name))


def to_impact_orms(entity: ShockEvent) -> list[ShockEventIndustryOrm]:
    return [
        ShockEventIndustryOrm(
            event_id=entity.event_id,
            industry_id=impact.industry_id,
            severity=impact.severity,
        )
        for impact in entity.industry_impacts
    ]
