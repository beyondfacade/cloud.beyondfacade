"""Outbound Boundary Gate — entity ↔ ORM 변환."""

from apps.admin.adapter.outbound.orms.security_setting_orm import SecuritySettingOrm
from apps.admin.domain.entities.security_setting_entity import SecuritySetting

_FIELDS = ("key", "enabled", "updated_at", "updated_by")


def to_orm(entity: SecuritySetting) -> SecuritySettingOrm:
    return SecuritySettingOrm(**{name: getattr(entity, name) for name in _FIELDS})


def to_entity(orm: SecuritySettingOrm) -> SecuritySetting:
    return SecuritySetting(**{name: getattr(orm, name) for name in _FIELDS})


def apply_to_orm(entity: SecuritySetting, orm: SecuritySettingOrm) -> None:
    for name in _FIELDS:
        setattr(orm, name, getattr(entity, name))
