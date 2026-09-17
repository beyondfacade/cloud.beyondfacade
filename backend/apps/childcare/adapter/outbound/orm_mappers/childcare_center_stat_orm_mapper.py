"""Outbound Boundary Gate — ORM → entity 변환 (Repository ↔ DB 경계)."""

from apps.childcare.adapter.outbound.orms.childcare_center_stat_orm import (
    ChildcareCenterStatOrm,
)
from apps.childcare.domain.entities.childcare_center_stat_entity import ChildcareCenterStat


def to_entity(orm: ChildcareCenterStatOrm) -> ChildcareCenterStat:
    return ChildcareCenterStat(
        base_date=orm.base_date,
        capacity=orm.capacity,
        child_count=orm.child_count,
        waiting_count=orm.waiting_count,
        class_count=orm.class_count,
        staff_count=orm.staff_count,
    )
