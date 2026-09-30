"""Outbound Boundary Gate — entity ↔ ORM 변환."""

from apps.admin.adapter.outbound.orms.ip_block_orm import IpBlockOrm
from apps.admin.domain.entities.ip_block_entity import IpBlock

_FIELDS = ("ip", "reason", "created_at", "expires_at", "created_by")


def to_orm(entity: IpBlock) -> IpBlockOrm:
    return IpBlockOrm(**{name: getattr(entity, name) for name in _FIELDS})


def to_entity(orm: IpBlockOrm) -> IpBlock:
    return IpBlock(**{name: getattr(orm, name) for name in _FIELDS})


def apply_to_orm(entity: IpBlock, orm: IpBlockOrm) -> None:
    for name in _FIELDS:
        setattr(orm, name, getattr(entity, name))
