"""Outbound Boundary Gate — ORM → entity 변환 (Repository ↔ DB 경계)."""

from apps.childcare.adapter.outbound.orm_mappers.childcare_center_stat_orm_mapper import (
    to_entity as to_stat_entity,
)
from apps.childcare.adapter.outbound.orms.childcare_center_orm import ChildcareCenterOrm
from apps.childcare.adapter.outbound.orms.childcare_center_stat_orm import (
    ChildcareCenterStatOrm,
)
from apps.childcare.domain.entities.childcare_center_entity import ChildcareCenter


def to_entity(orm: ChildcareCenterOrm, stat: ChildcareCenterStatOrm) -> ChildcareCenter:
    return ChildcareCenter(
        center_id=orm.center_id,
        name=orm.name,
        type_name=orm.type_name,
        status_name=orm.status_name,
        district_code=orm.district_code,
        address=orm.address,
        zipcode=orm.zipcode,
        tel=orm.tel,
        lat=orm.lat,
        lng=orm.lng,
        approved_on=orm.approved_on,
        paused_from=orm.paused_from,
        paused_until=orm.paused_until,
        abolished_on=orm.abolished_on,
        stat=to_stat_entity(stat),
    )
